"""Account-scoped vector persistence. Callers own the transaction; no external I/O."""

import hashlib
import math
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import DocumentPage, DocumentVector, ResearchDocument
from app.documents.contracts import PdfChunk
from app.documents.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EmbeddingBatch,
)
from app.documents.gemini import GEMINI_MODEL
from app.documents.repository import DocumentRepository


def valid_batch(batch: EmbeddingBatch, count: int) -> bool:
    return (
        batch.model in {EMBEDDING_MODEL, GEMINI_MODEL}
        and batch.dimensions == EMBEDDING_DIMENSIONS
        and len(batch.vectors) == count
        and all(
            len(vector) == EMBEDDING_DIMENSIONS
            and all(math.isfinite(x) for x in vector)
            and math.isclose(math.hypot(*vector), 1.0, rel_tol=1e-5)
            for vector in batch.vectors
        )
    )


def invalid() -> AppError:
    return AppError(
        code="invalid_document_vectors",
        message="Vectors do not match the current paper text.",
        status_code=409,
    )


class VectorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace(
        self,
        owner: UUID,
        document: UUID,
        chunks: Sequence[PdfChunk],
        batch: EmbeddingBatch,
    ) -> None:
        # Serialize replacements and block deletion/status changes during validation.
        row = await self.session.scalar(
            select(ResearchDocument)
            .where(
                ResearchDocument.id == document,
                ResearchDocument.owner_id == owner,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            await DocumentRepository(self.session).owned(owner, document)
        pages = await DocumentRepository(self.session).pages(owner, document)
        if not 1 <= len(chunks) <= 2000 or not valid_batch(batch, len(chunks)):
            raise invalid()
        by_number = {page.number: page for page in pages}
        seen: set[tuple[int, int]] = set()
        records: list[DocumentVector] = []
        for chunk, vector in zip(chunks, batch.vectors, strict=True):
            page = by_number.get(chunk.page)
            identity = (chunk.page, chunk.start)
            if (
                page is None
                or identity in seen
                or chunk.end <= chunk.start
                or page.text[chunk.start : chunk.end] != chunk.text
                or {"start": chunk.start, "end": chunk.end, "text": chunk.text}
                not in page.chunks
            ):
                raise invalid()
            seen.add(identity)
            records.append(
                DocumentVector(
                    page_id=page.id,
                    start=chunk.start,
                    end_offset=chunk.end,
                    text_sha256=hashlib.sha256(chunk.text.encode()).hexdigest(),
                    model=batch.model,
                    embedding=list(vector),
                )
            )
        # A partial index is not silently promoted to a complete document index.
        expected = {
            (page.number, int(c["start"])) for page in pages for c in page.chunks
        }
        if seen != expected:
            raise invalid()
        await self.session.execute(
            delete(DocumentVector).where(
                DocumentVector.page_id.in_([page.id for page in pages])
            )
        )
        self.session.add_all(records)
        await self.session.flush()

    async def nearest(
        self, owner: UUID, document: UUID, query: EmbeddingBatch, *, limit: int = 5
    ) -> list[PdfChunk]:
        await DocumentRepository(self.session).pages(owner, document)
        if not 1 <= limit <= 10 or not valid_batch(query, 1):
            raise invalid()
        if self.session.get_bind().dialect.name != "postgresql":
            raise AppError(
                code="vector_search_unavailable",
                message="Vector search requires PostgreSQL.",
                status_code=503,
            )
        rows = await self.session.execute(
            select(DocumentVector, DocumentPage)
            .join(DocumentPage, DocumentPage.id == DocumentVector.page_id)
            .join(ResearchDocument, ResearchDocument.id == DocumentPage.document_id)
            .where(
                ResearchDocument.owner_id == owner,
                ResearchDocument.id == document,
                ResearchDocument.status == "ready",
                DocumentVector.model == query.model,
            )
            .order_by(
                DocumentVector.embedding.cosine_distance(list(query.vectors[0])),
                DocumentPage.number,
                DocumentVector.start,
            )
            .limit(limit)
        )
        results: list[PdfChunk] = []
        for stored, page in rows:
            excerpt = page.text[stored.start : stored.end_offset]
            if hashlib.sha256(excerpt.encode()).hexdigest() != stored.text_sha256:
                continue
            if not 0 < len(excerpt) <= 1200:
                continue
            results.append(
                PdfChunk(
                    page=page.number,
                    start=stored.start,
                    end=stored.end_offset,
                    text=excerpt,
                )
            )
        return results
