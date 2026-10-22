"""Authenticated, bounded PDF transport; business state lives in document services."""

import asyncio
from datetime import UTC, datetime
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import (
    AnswerReservation,
    EmbeddingReservation,
    IndexJob,
    ResearchDocument,
)
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.database import get_database, get_session
from app.documents.answer_service import PaperAnswers
from app.documents.answer_usage import (
    ANSWER_DISCLOSURE,
    ANSWER_DISCLOSURE_TEXT,
    RESERVED_CALLS,
    AnswerRequest,
)
from app.documents.answers import AnswerResult
from app.documents.contracts import MAX_PDF_BYTES, PdfPage
from app.documents.embeddings import EmbeddingError
from app.documents.gemini_answers import ANSWER_MODEL, GeminiAnswerProvider
from app.documents.history import ReadingHistoryEntry, read_history
from app.documents.hybrid import HybridResult
from app.documents.indexing import IndexRepository
from app.documents.providers import configured, create_embedder, policy
from app.documents.repository import DocumentRepository
from app.documents.retrieval import PassageQuery, PassageResult, retrieve
from app.documents.semantic import SemanticQuery, SemanticSearch
from app.documents.service import DocumentService
from app.documents.storage import SupabaseDocumentStorage


def private_response(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization"


router = APIRouter(
    prefix="/documents", tags=["documents"], dependencies=[Depends(private_response)]
)
Principal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]
Session = Annotated[AsyncSession, Depends(get_session)]


class DocumentSummary(BaseModel):
    id: UUID
    filename: str
    status: str
    reason: str | None
    warnings: list[str]


class DocumentList(BaseModel):
    uploads_enabled: bool
    documents: list[DocumentSummary]


class DocumentCreated(BaseModel):
    id: UUID


def enabled(request: Request) -> bool:
    settings = cast(Settings, request.app.state.settings)
    return bool(
        settings.document_uploads_enabled
        and settings.supabase_url
        and settings.supabase_storage_service_key
        and settings.document_scanner_host
    )


def summary(row: ResearchDocument) -> DocumentSummary:
    return DocumentSummary(
        id=row.id,
        filename=row.filename,
        status=row.status,
        reason=row.reason,
        warnings=row.warnings,
    )


@router.get("/paper/{paper_id}", response_model=DocumentList)
async def list_documents(
    paper_id: UUID, request: Request, principal: Principal, session: Session
) -> DocumentList:
    rows = await session.scalars(
        select(ResearchDocument)
        .where(
            ResearchDocument.owner_id == principal.owner_id,
            ResearchDocument.paper_id == paper_id,
        )
        .order_by(ResearchDocument.created_at.desc())
    )
    return DocumentList(
        uploads_enabled=enabled(request), documents=[summary(row) for row in rows]
    )


@router.get("/{document_id}", response_model=DocumentSummary)
async def read_document(
    document_id: UUID, principal: Principal, session: Session
) -> DocumentSummary:
    return summary(
        await DocumentRepository(session).owned(principal.owner_id, document_id)
    )


@router.get("/{document_id}/pages", response_model=list[PdfPage])
async def read_pages(
    document_id: UUID, principal: Principal, session: Session
) -> list[PdfPage]:
    pages = await DocumentRepository(session).pages(principal.owner_id, document_id)
    return [PdfPage(number=page.number, text=page.text) for page in pages]


@router.get(
    "/{document_id}/file",
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            }
        }
    },
)
async def read_original(
    document_id: UUID, request: Request, principal: Principal, session: Session
) -> Response:
    await session.commit()
    settings = cast(Settings, request.app.state.settings)
    storage = SupabaseDocumentStorage(settings)
    try:
        content = await DocumentService(
            get_database(request).session_factory,
            storage,
            settings.document_storage_bucket,
        ).original(principal.owner_id, document_id)
    finally:
        await storage.aclose()
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, no-store",
            "Vary": "Authorization",
            "Content-Disposition": 'inline; filename="paper.pdf"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID, principal: Principal, session: Session
) -> Response:
    row = await DocumentRepository(session).owned(principal.owner_id, document_id)
    await session.delete(row)
    await session.flush()
    return Response(status_code=204)


@router.post(
    "/paper/{paper_id}",
    response_model=DocumentCreated,
    status_code=202,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def upload_document(
    paper_id: UUID,
    request: Request,
    principal: Principal,
    session: Session,
    filename: Annotated[str, Query(min_length=1, max_length=255)] = "paper.pdf",
) -> DocumentCreated:
    if not enabled(request):
        raise AppError(
            code="documents_not_configured",
            message="PDF uploads are not enabled yet.",
            status_code=503,
        )
    if (
        request.headers.get("content-type", "").split(";")[0].strip().lower()
        != "application/pdf"
    ):
        raise AppError(
            code="invalid_document_type", message="Upload a PDF file.", status_code=415
        )
    length = request.headers.get("content-length")
    if length and (
        not length.isascii()
        or not length.isdecimal()
        or len(length) > 9
        or int(length) > MAX_PDF_BYTES
    ):
        raise AppError(
            code="document_too_large", message="PDF limit is 20 MiB.", status_code=413
        )
    content = bytearray()
    try:
        async with asyncio.timeout(30):
            async for chunk in request.stream():
                if len(content) + len(chunk) > MAX_PDF_BYTES:
                    raise AppError(
                        code="document_too_large",
                        message="PDF limit is 20 MiB.",
                        status_code=413,
                    )
                content.extend(chunk)
    except TimeoutError as exc:
        raise AppError(
            code="upload_timeout", message="Upload timed out.", status_code=408
        ) from exc
    # Authentication may have just created the owner in this shared session.
    await session.commit()
    settings = cast(Settings, request.app.state.settings)
    storage = SupabaseDocumentStorage(settings)
    try:
        service = DocumentService(
            get_database(request).session_factory,
            storage,
            settings.document_storage_bucket,
        )
        id = await service.upload(
            principal.owner_id, paper_id, filename, bytes(content)
        )
    finally:
        await storage.aclose()
    return DocumentCreated(id=id)


@router.post("/{document_id}/passages", response_model=PassageResult)
async def search_passages(
    document_id: UUID, body: PassageQuery, principal: Principal, session: Session
) -> PassageResult:
    return await retrieve(session, principal.owner_id, document_id, body)


class IndexConsent(BaseModel):
    accepted: Literal[True]
    disclosure_version: Literal["paper-embeddings-v1", "paper-gemini-v1"]


class IndexStatus(BaseModel):
    enabled: bool
    status: Literal[
        "not_started", "queued", "processing", "completed", "failed", "cancelled"
    ]
    reason: str | None
    retry_at: datetime | None
    disclosure_version: str
    query_disclosure_version: str
    provider: str
    reserved_today: int
    daily_limit: int


def indexing_available(request: Request) -> bool:
    settings = cast(Settings, request.app.state.settings)
    return bool(
        settings.document_indexing_enabled
        and configured(settings)
        and get_database(request).engine.dialect.name == "postgresql"
    )


@router.get("/{document_id}/index", response_model=IndexStatus)
async def indexing_status(
    document_id: UUID, request: Request, principal: Principal, session: Session
) -> IndexStatus:
    await DocumentRepository(session).owned(principal.owner_id, document_id)
    job = await session.scalar(
        select(IndexJob).where(IndexJob.document_id == document_id)
    )
    used = await session.scalar(
        select(func.coalesce(func.sum(EmbeddingReservation.reserved_tokens), 0)).where(
            EmbeddingReservation.owner_id == principal.owner_id,
            EmbeddingReservation.day == datetime.now(UTC).date(),
        )
    )
    current_policy = policy(cast(Settings, request.app.state.settings))
    changed = job is not None and job.disclosure_version != current_policy.disclosure
    return IndexStatus(
        enabled=indexing_available(request),
        status=job.status if job and not changed else "not_started",
        reason="provider_changed" if changed else job.last_error if job else None,
        retry_at=job.available_at if job and job.status == "queued" else None,
        disclosure_version=current_policy.disclosure,
        query_disclosure_version=current_policy.query_disclosure,
        provider=current_policy.label,
        reserved_today=int(used or 0),
        daily_limit=cast(
            Settings, request.app.state.settings
        ).document_embedding_daily_limit,
    )


@router.post("/{document_id}/index", response_model=DocumentCreated, status_code=202)
async def start_indexing(
    document_id: UUID,
    body: IndexConsent,
    request: Request,
    principal: Principal,
    session: Session,
) -> DocumentCreated:
    await DocumentRepository(session).owned(principal.owner_id, document_id)
    if not indexing_available(request):
        raise AppError(
            code="indexing_not_configured",
            message="Semantic indexing is not enabled yet.",
            status_code=503,
        )
    current_policy = policy(cast(Settings, request.app.state.settings))
    if body.disclosure_version != current_policy.disclosure:
        raise AppError(
            code="disclosure_changed",
            message="Refresh and review the current provider disclosure.",
            status_code=409,
        )
    job_id = await IndexRepository(session, current_policy).enqueue(
        principal.owner_id, document_id, accepted=body.accepted
    )
    return DocumentCreated(id=job_id)


@router.delete("/{document_id}/index", status_code=204)
async def cancel_indexing(
    document_id: UUID, principal: Principal, session: Session
) -> Response:
    await IndexRepository(session).cancel(principal.owner_id, document_id)
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})


@router.post("/{document_id}/semantic-passages", response_model=HybridResult)
async def search_semantic_passages(
    document_id: UUID,
    body: SemanticQuery,
    request: Request,
    principal: Principal,
    session: Session,
) -> HybridResult:
    await DocumentRepository(session).pages(principal.owner_id, document_id)
    if not indexing_available(request):
        raise AppError(
            code="semantic_search_unavailable",
            message=(
                "Semantic search is not configured yet. Keyword search is available."
            ),
            status_code=503,
        )
    await session.commit()
    settings = cast(Settings, request.app.state.settings)
    provider = None
    try:
        provider = create_embedder(settings, query=True)
        return await SemanticSearch(
            get_database(request).session_factory,
            provider,
            enabled=True,
            daily_limit=settings.document_embedding_daily_limit,
            embedding_policy=policy(settings),
        ).search(principal.owner_id, document_id, body)
    except EmbeddingError as exc:
        raise AppError(
            code="semantic_provider_unavailable",
            message=(
                "Semantic search could not finish. Try again later or use "
                "keyword search. Reserved usage remains counted."
            ),
            status_code=503,
        ) from exc
    finally:
        if provider is not None:
            await provider.aclose()


class AnswerStatus(BaseModel):
    enabled: bool
    provider: str
    model: str
    disclosure_version: str
    disclosure: str
    reserved_calls_today: int
    daily_call_limit: int
    calls_reserved_per_question: int


def answers_available(request: Request) -> bool:
    settings = cast(Settings, request.app.state.settings)
    return bool(
        settings.document_answers_enabled
        and settings.gemini_api_key
        and get_database(request).engine.dialect.name == "postgresql"
    )


@router.get("/{document_id}/answers", response_model=AnswerStatus)
async def answer_status(
    document_id: UUID, request: Request, principal: Principal, session: Session
) -> AnswerStatus:
    await DocumentRepository(session).owned(principal.owner_id, document_id)
    settings = cast(Settings, request.app.state.settings)
    used = await session.scalar(
        select(func.coalesce(func.sum(AnswerReservation.reserved_calls), 0)).where(
            AnswerReservation.owner_id == principal.owner_id,
            AnswerReservation.day == datetime.now(UTC).date(),
        )
    )
    return AnswerStatus(
        enabled=answers_available(request),
        provider="Google Gemini",
        model=ANSWER_MODEL,
        disclosure_version=ANSWER_DISCLOSURE,
        disclosure=ANSWER_DISCLOSURE_TEXT,
        reserved_calls_today=int(used or 0),
        daily_call_limit=settings.document_answer_daily_call_limit,
        calls_reserved_per_question=RESERVED_CALLS,
    )


@router.post("/{document_id}/answers", response_model=AnswerResult)
async def ask_paper(
    document_id: UUID,
    body: AnswerRequest,
    request: Request,
    principal: Principal,
    session: Session,
) -> AnswerResult:
    await DocumentRepository(session).pages(principal.owner_id, document_id)
    if not answers_available(request):
        raise AppError(
            code="paper_answers_unavailable",
            message="Paper answers are not enabled yet.",
            status_code=503,
        )
    await session.commit()
    settings = cast(Settings, request.app.state.settings)
    provider = GeminiAnswerProvider(settings)
    try:
        return await PaperAnswers(
            get_database(request).session_factory,
            provider,
            enabled=True,
            daily_call_limit=settings.document_answer_daily_call_limit,
        ).ask(principal.owner_id, document_id, body)
    finally:
        await provider.aclose()


@router.get("/{document_id}/reading-history", response_model=list[ReadingHistoryEntry])
async def reading_history(
    document_id: UUID, principal: Principal, session: Session
) -> list[ReadingHistoryEntry]:
    return await read_history(session, principal.owner_id, document_id)
