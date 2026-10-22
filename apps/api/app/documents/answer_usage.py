"""Reservation primitive only; caller must commit before any provider I/O."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import AccountOwner, AnswerReservation
from app.documents.answers import StrictModel
from app.documents.gemini_answers import ANSWER_MODEL
from app.documents.repository import DocumentRepository

ANSWER_DISCLOSURE = "paper-answer-gemini-v1"
ANSWER_DISCLOSURE_TEXT = (
    "Send your question and retrieved paper text to Google Gemini to generate "
    "and check an answer. Gemini free-tier data may be used to improve Google's "
    "products. Model checks can miss unsupported details. No Gmail messages or "
    "CVs are included."
)
RESERVED_CALLS = 3


class AnswerRequest(StrictModel):
    request_id: UUID = Field(strict=False)
    question: str = Field(min_length=1, max_length=500)
    accepted: Literal[True]
    disclosure_version: Literal["paper-answer-gemini-v1"]

    @field_validator("accepted", mode="before")
    @classmethod
    def explicit_boolean(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit consent is required")
        return value

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question cannot be blank")
        return value


async def reserve_answer(
    session: AsyncSession,
    owner: UUID,
    document: UUID,
    request: AnswerRequest,
    *,
    daily_call_limit: int,
) -> UUID:
    if daily_call_limit < RESERVED_CALLS:
        raise ValueError("Limit must allow at least one answer")
    await DocumentRepository(session).pages(owner, document)
    locked_owner = await session.scalar(
        select(AccountOwner).where(AccountOwner.id == owner).with_for_update()
    )
    if locked_owner is None:
        raise AppError(
            code="owner_not_found", message="Account unavailable.", status_code=404
        )
    existing = await session.scalar(
        select(AnswerReservation.id).where(
            AnswerReservation.owner_id == owner,
            AnswerReservation.request_id == request.request_id,
        )
    )
    if existing is not None:
        raise AppError(
            code="answer_request_used",
            message="This request was already reserved. Do not resend automatically.",
            status_code=409,
        )
    now = datetime.now(UTC)
    used = await session.scalar(
        select(func.coalesce(func.sum(AnswerReservation.reserved_calls), 0)).where(
            AnswerReservation.owner_id == owner, AnswerReservation.day == now.date()
        )
    )
    if int(used or 0) + RESERVED_CALLS > daily_call_limit:
        raise AppError(
            code="answer_daily_quota",
            message="Today's answer allowance is used. Try after midnight UTC.",
            status_code=429,
        )
    row = AnswerReservation(
        owner_id=owner,
        document_id=document,
        request_id=request.request_id,
        day=now.date(),
        reserved_calls=RESERVED_CALLS,
        disclosure_version=request.disclosure_version,
        model=ANSWER_MODEL,
        accepted_at=now,
    )
    session.add(row)
    await session.flush()
    return row.id
