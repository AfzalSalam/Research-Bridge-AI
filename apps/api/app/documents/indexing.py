"""Durable indexing: caller commits leases/reservations before provider I/O."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import AccountOwner, EmbeddingReservation, IndexJob, ResearchDocument
from app.documents.contracts import PdfChunk
from app.documents.embeddings import EmbeddingBatch
from app.documents.providers import OPENAI, EmbeddingPolicy
from app.documents.repository import DocumentRepository
from app.documents.vectors import VectorRepository

DISCLOSURE_VERSION = "paper-embeddings-v1"


@dataclass(frozen=True)
class IndexLease:
    job_id: UUID
    document_id: UUID
    owner_id: UUID
    token: UUID
    chunks: tuple[PdfChunk, ...]


class IndexRepository:
    def __init__(self, session: AsyncSession, policy: EmbeddingPolicy = OPENAI) -> None:
        self.session, self.policy = session, policy

    async def enqueue(self, owner: UUID, document: UUID, *, accepted: bool) -> UUID:
        if not accepted:
            raise AppError(
                code="disclosure_required",
                message="Review and accept paper AI processing first.",
                status_code=422,
            )
        await self.session.scalar(
            select(AccountOwner).where(AccountOwner.id == owner).with_for_update()
        )
        await DocumentRepository(self.session).pages(owner, document)
        existing = await self.session.scalar(
            select(IndexJob).where(IndexJob.document_id == document).with_for_update()
        )
        if existing:
            if existing.disclosure_version != self.policy.disclosure:
                existing.disclosure_version = self.policy.disclosure
                existing.accepted_at = datetime.now(UTC)
                existing.available_at = datetime.now(UTC)
                existing.status, existing.attempts = "queued", 0
                existing.lease_token, existing.lease_until = None, None
                existing.last_error = None
                await self.session.flush()
            return existing.id
        now = datetime.now(UTC)
        job = IndexJob(
            document_id=document,
            available_at=now,
            disclosure_version=self.policy.disclosure,
            accepted_at=now,
        )
        self.session.add(job)
        await self.session.flush()
        return job.id

    async def claim(
        self, daily_limit: int, now: datetime | None = None
    ) -> IndexLease | None:
        if daily_limit <= 0:
            raise ValueError("daily_limit must be positive")
        now = now or datetime.now(UTC)
        job = await self.session.scalar(
            select(IndexJob)
            .where(
                IndexJob.disclosure_version == self.policy.disclosure,
                or_(
                    (IndexJob.status == "queued") & (IndexJob.available_at <= now),
                    (IndexJob.status == "processing") & (IndexJob.lease_until <= now),
                ),
            )
            .order_by(IndexJob.available_at, IndexJob.id)
            .with_for_update(skip_locked=True)
            .limit(1)
            .execution_options(populate_existing=True)
        )
        if job is None:
            return None
        if job.attempts >= 3:
            job.status, job.last_error = "failed", "retry_limit"
            job.lease_until, job.lease_token = None, None
            return None
        doc = await self.session.get(ResearchDocument, job.document_id)
        if (
            doc is None
            or doc.status != "ready"
            or job.disclosure_version != self.policy.disclosure
        ):
            job.status, job.last_error = "failed", "document_unavailable"
            return None
        # Enqueue holds the owner before updating a job. Never wait on that owner
        # while holding this job lock: let the next worker pass retry instead.
        owner = await self.session.scalar(
            select(AccountOwner)
            .where(AccountOwner.id == doc.owner_id)
            .with_for_update(skip_locked=True)
        )
        if owner is None:
            return None
        pages = await DocumentRepository(self.session).pages(doc.owner_id, doc.id)
        chunks = tuple(PdfChunk(page=p.number, **c) for p in pages for c in p.chunks)
        if (
            not chunks
            or len(chunks) > 2000
            or any(
                p.text[int(c["start"]) : int(c["end"])] != c["text"]
                for p in pages
                for c in p.chunks
            )
        ):
            job.status, job.last_error = "failed", "invalid_chunks"
            return None
        # UTF-8 bytes bound token count; reserve all three provider attempts.
        required = (
            sum(
                len((self.policy.document_prefix + c.text).encode("utf-8"))
                for c in chunks
            )
            * 3
        )
        if required > daily_limit:
            job.status, job.last_error = "failed", "document_exceeds_quota"
            job.lease_until, job.lease_token = None, None
            return None
        used = await self.session.scalar(
            select(
                func.coalesce(func.sum(EmbeddingReservation.reserved_tokens), 0)
            ).where(
                EmbeddingReservation.owner_id == doc.owner_id,
                EmbeddingReservation.day == now.date(),
            )
        )
        if int(used or 0) + required > daily_limit:
            job.status, job.last_error = "queued", "daily_quota"
            job.available_at = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            job.lease_until, job.lease_token = None, None
            return None
        token = uuid4()
        self.session.add(
            EmbeddingReservation(
                owner_id=doc.owner_id,
                lease_token=token,
                day=now.date(),
                reserved_tokens=required,
            )
        )
        job.status, job.lease_token = "processing", token
        job.lease_until = now + timedelta(minutes=3)
        job.attempts += 1
        job.last_error = None
        await self.session.flush()
        return IndexLease(job.id, doc.id, doc.owner_id, token, chunks)

    async def current(
        self, lease: IndexLease, now: datetime | None = None
    ) -> IndexJob | None:
        job: IndexJob | None = await self.session.scalar(
            select(IndexJob)
            .where(
                IndexJob.id == lease.job_id,
                IndexJob.document_id == lease.document_id,
                IndexJob.status == "processing",
                IndexJob.lease_token == lease.token,
                IndexJob.lease_until > (now or datetime.now(UTC)),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return job

    async def renew(self, lease: IndexLease) -> bool:
        job = await self.current(lease)
        if job is None:
            return False
        doc = await self.session.get(ResearchDocument, lease.document_id)
        if doc is None or doc.owner_id != lease.owner_id or doc.status != "ready":
            job.status, job.last_error = "failed", "document_unavailable"
            job.lease_until, job.lease_token = None, None
            return False
        reservation = await self.session.scalar(
            select(EmbeddingReservation).where(
                EmbeddingReservation.lease_token == lease.token
            )
        )
        if reservation is None or reservation.day != datetime.now(UTC).date():
            job.status, job.last_error = "queued", "reservation_day_expired"
            job.available_at = datetime.now(UTC)
            job.lease_until, job.lease_token = None, None
            return False
        job.lease_until = datetime.now(UTC) + timedelta(minutes=3)
        return True

    async def finish(
        self,
        lease: IndexLease,
        batch: EmbeddingBatch | None,
        *,
        error: str = "",
        retry_after: int = 0,
    ) -> bool:
        job = await self.current(lease)
        if job is None:
            return False
        if batch is not None:
            if (
                batch.model != self.policy.model
                or job.disclosure_version != self.policy.disclosure
            ):
                raise AppError(
                    code="embedding_model_mismatch",
                    message="Paper provider changed. Prepare it again.",
                    status_code=409,
                )
            await VectorRepository(self.session).replace(
                lease.owner_id, lease.document_id, lease.chunks, batch
            )
            job.status, job.last_error = "completed", None
        else:
            job.status = "queued" if retry_after and job.attempts < 3 else "failed"
            job.available_at = datetime.now(UTC) + timedelta(
                seconds=max(30, min(retry_after, 3600))
            )
            job.last_error = error[:100]
        job.lease_until, job.lease_token = None, None
        await self.session.flush()
        return True

    async def cancel(self, owner: UUID, document: UUID) -> None:
        await DocumentRepository(self.session).owned(owner, document)
        job = await self.session.scalar(
            select(IndexJob).where(IndexJob.document_id == document).with_for_update()
        )
        if job is not None and job.status in {"queued", "processing"}:
            job.status, job.last_error = "cancelled", "cancelled_by_owner"
            job.lease_until, job.lease_token = None, None
            await self.session.flush()
