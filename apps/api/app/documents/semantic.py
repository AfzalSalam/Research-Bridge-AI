"""Consented, budgeted query embedding. No question text is persisted or logged."""

from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID, uuid4

from pydantic import Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models import AccountOwner, EmbeddingReservation, IndexJob
from app.documents.embeddings import EmbeddingBatch, EmbeddingError
from app.documents.hybrid import HybridResult, retrieve_hybrid
from app.documents.providers import GEMINI, OPENAI, EmbeddingPolicy
from app.documents.repository import DocumentRepository
from app.documents.retrieval import PassageQuery
from app.documents.vectors import valid_batch

QUERY_DISCLOSURE_VERSION = "paper-query-embeddings-v1"


class SemanticQuery(PassageQuery):
    accepted: Literal[True]
    disclosure_version: Literal["paper-query-embeddings-v1", "paper-query-gemini-v1"]
    query: str = Field(min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a question or search phrase.")
        return value


class QueryEmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> EmbeddingBatch: ...


async def reserve_query(
    session: AsyncSession,
    owner: UUID,
    document: UUID,
    request: SemanticQuery,
    *,
    daily_limit: int,
) -> None:
    """Caller must commit this transaction before provider I/O."""
    if daily_limit <= 0:
        raise ValueError("daily_limit must be positive")
    await DocumentRepository(session).pages(owner, document)
    await session.scalar(
        select(AccountOwner).where(AccountOwner.id == owner).with_for_update()
    )
    job = await session.scalar(
        select(IndexJob).where(
            IndexJob.document_id == document,
            IndexJob.status == "completed",
            IndexJob.disclosure_version
            == (
                GEMINI.disclosure
                if request.disclosure_version == GEMINI.query_disclosure
                else OPENAI.disclosure
            ),
        )
    )
    if job is None:
        raise AppError(
            code="paper_index_required",
            message="Prepare this paper for semantic search first.",
            status_code=409,
        )
    now = datetime.now(UTC)
    used = await session.scalar(
        select(func.coalesce(func.sum(EmbeddingReservation.reserved_tokens), 0)).where(
            EmbeddingReservation.owner_id == owner,
            EmbeddingReservation.day == now.date(),
        )
    )
    # Same conservative allowance as indexing: UTF-8 bytes times three attempts.
    prefix = (
        GEMINI.query_prefix
        if request.disclosure_version == GEMINI.query_disclosure
        else ""
    )
    required = len((prefix + request.query).encode("utf-8")) * 3
    if int(used or 0) + required > daily_limit:
        raise AppError(
            code="embedding_daily_quota",
            message="Today's paper AI budget is used. Try after midnight UTC.",
            status_code=429,
        )
    session.add(
        EmbeddingReservation(
            owner_id=owner,
            lease_token=uuid4(),
            day=now.date(),
            reserved_tokens=required,
        )
    )
    await session.flush()


class SemanticSearch:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        provider: QueryEmbeddingProvider,
        *,
        enabled: bool,
        daily_limit: int,
        embedding_policy: EmbeddingPolicy = OPENAI,
    ) -> None:
        self.sessions, self.provider = sessions, provider
        self.enabled, self.daily_limit = enabled, daily_limit
        self.policy = embedding_policy

    async def search(
        self, owner: UUID, document: UUID, request: SemanticQuery
    ) -> HybridResult:
        if request.disclosure_version != self.policy.query_disclosure:
            raise AppError(
                code="disclosure_changed",
                message="Refresh and review the current provider disclosure.",
                status_code=409,
            )
        async with self.sessions() as session:
            await DocumentRepository(session).pages(owner, document)
            if not self.enabled or session.get_bind().dialect.name != "postgresql":
                raise AppError(
                    code="semantic_search_unavailable",
                    message="Semantic search is not configured yet.",
                    status_code=503,
                )
            await reserve_query(
                session, owner, document, request, daily_limit=self.daily_limit
            )
            await session.commit()
        # No DB locks span network I/O. Failed/unknown calls keep their reservation.
        batch = await self.provider.embed([request.query])
        if batch.model != self.policy.model or not valid_batch(batch, 1):
            raise EmbeddingError("invalid_embedding_response")
        async with self.sessions() as session:
            return await retrieve_hybrid(session, owner, document, request, batch)
