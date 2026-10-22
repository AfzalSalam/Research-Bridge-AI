"""Owner-scoped completed reading snapshots; never sent back to the provider."""

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import AccountOwner, ReadingAnswer, ResearchDocument
from app.documents.answer_usage import AnswerRequest
from app.documents.answers import AnswerResult
from app.documents.gemini_answers import ANSWER_MODEL
from app.documents.repository import DocumentRepository


class ReadingHistoryEntry(BaseModel):
    id: UUID
    question: str
    result: AnswerResult
    model: str
    created_at: datetime


async def read_history(
    session: AsyncSession, owner: UUID, document: UUID
) -> list[ReadingHistoryEntry]:
    await DocumentRepository(session).owned(owner, document)
    rows = await session.scalars(
        select(ReadingAnswer)
        .where(ReadingAnswer.owner_id == owner, ReadingAnswer.document_id == document)
        .order_by(ReadingAnswer.created_at.desc(), ReadingAnswer.id.desc())
        .limit(20)
    )
    return [
        ReadingHistoryEntry(
            id=row.id,
            question=row.question,
            result=AnswerResult.model_validate_json(json.dumps(row.result)),
            model=row.model,
            created_at=row.created_at,
        )
        for row in rows
    ]


async def ensure_unused(
    session: AsyncSession, owner: UUID, request: AnswerRequest
) -> None:
    if (
        await session.scalar(
            select(ReadingAnswer.id).where(
                ReadingAnswer.owner_id == owner,
                ReadingAnswer.request_id == request.request_id,
            )
        )
        is not None
    ):
        raise AppError(
            code="answer_request_used",
            message="This question request was already used. Refresh reading history.",
            status_code=409,
        )


async def save_history(
    session: AsyncSession,
    owner: UUID,
    document: UUID,
    request: AnswerRequest,
    result: AnswerResult,
) -> None:
    # Match reservation lock order; serialize request IDs across this account.
    account = await session.scalar(
        select(AccountOwner).where(AccountOwner.id == owner).with_for_update()
    )
    if account is None:
        raise AppError(
            code="owner_not_found", message="Account unavailable.", status_code=404
        )
    # Serialize deletion against saving without holding a lock during provider I/O.
    row = await session.scalar(
        select(ResearchDocument)
        .where(ResearchDocument.id == document, ResearchDocument.owner_id == owner)
        .with_for_update()
    )
    if row is None:
        raise AppError(
            code="document_not_found", message="Document not found.", status_code=404
        )
    await ensure_unused(session, owner, request)
    session.add(
        ReadingAnswer(
            owner_id=owner,
            document_id=document,
            request_id=request.request_id,
            question=request.question,
            result=result.model_dump(mode="json"),
            model=ANSWER_MODEL,
            disclosure_version=request.disclosure_version,
        )
    )
    await session.flush()
