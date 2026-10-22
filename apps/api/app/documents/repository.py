from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.documents import DocumentJob, DocumentPage, ResearchDocument
from app.documents.contracts import PdfExtraction


@dataclass(frozen=True)
class DocumentLease:
    job_id: UUID
    document_id: UUID
    owner_id: UUID
    token: UUID
    sha256: str


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def owned(self, owner: UUID, document: UUID) -> ResearchDocument:
        row = await self.session.scalar(
            select(ResearchDocument).where(
                ResearchDocument.id == document, ResearchDocument.owner_id == owner
            )
        )
        if row is None:
            raise AppError(
                code="document_not_found",
                message="Document not found.",
                status_code=404,
            )
        return row

    async def pages(self, owner: UUID, document: UUID) -> list[DocumentPage]:
        row = await self.owned(owner, document)
        if row.status != "ready":
            raise AppError(
                code="document_not_ready",
                message="Document is not ready.",
                status_code=409,
            )
        return list(
            await self.session.scalars(
                select(DocumentPage)
                .where(DocumentPage.document_id == document)
                .order_by(DocumentPage.number)
            )
        )

    async def enqueue(self, owner: UUID, document: UUID) -> None:
        await self.owned(owner, document)
        changed = await self.session.scalar(
            update(ResearchDocument)
            .where(
                ResearchDocument.id == document,
                ResearchDocument.owner_id == owner,
                ResearchDocument.status == "uploading",
            )
            .values(status="quarantined")
            .returning(ResearchDocument.id)
        )
        if changed is None:
            raise AppError(
                code="document_state_conflict",
                message="Upload already finalized.",
                status_code=409,
            )
        self.session.add(
            DocumentJob(document_id=document, available_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def claim(self, now: datetime | None = None) -> DocumentLease | None:
        now = now or datetime.now(UTC)
        # Caller commits before doing external work; PostgreSQL locks one job only.
        while True:
            job = await self.session.scalar(
                select(DocumentJob)
                .where(
                    or_(
                        (DocumentJob.status == "queued")
                        & (DocumentJob.available_at <= now),
                        (DocumentJob.status == "processing")
                        & (DocumentJob.lease_until <= now),
                    )
                )
                .order_by(DocumentJob.available_at, DocumentJob.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if job is None:
                return None
            document = await self.session.get(ResearchDocument, job.document_id)
            if document is None:
                await self.session.delete(job)
                await self.session.flush()
                continue
            if job.attempts >= 3:
                job.status, job.last_error = "failed", "retry_limit"
                job.lease_until, job.lease_token = None, None
                document.status, document.reason = "failed", "retry_limit"
                await self.session.flush()
                continue
            job.status, document.status = "processing", "processing"
            job.attempts += 1
            job.lease_token = uuid4()
            job.lease_until = now + timedelta(minutes=5)
            await self.session.flush()
            return DocumentLease(
                job.id, document.id, document.owner_id, job.lease_token, document.sha256
            )

    async def finish(
        self,
        lease: DocumentLease,
        result: PdfExtraction,
        now: datetime | None = None,
        *,
        retry_after: int = 0,
    ) -> bool:
        now = now or datetime.now(UTC)
        job = await self.session.scalar(
            select(DocumentJob)
            .where(
                DocumentJob.id == lease.job_id,
                DocumentJob.lease_token == lease.token,
                DocumentJob.document_id == lease.document_id,
                DocumentJob.status == "processing",
                DocumentJob.lease_until > now,
            )
            .with_for_update()
        )
        if job is None:
            return False
        document = await self.session.get(ResearchDocument, lease.document_id)
        if document is None:
            return False
        job.lease_until, job.lease_token = None, None
        if result.status == "failed" and job.attempts < 3:
            job.status = "queued"
            job.available_at = now + timedelta(
                seconds=max(30 * job.attempts, min(retry_after, 3600))
            )
            job.last_error = result.reason[:100]
            document.status, document.reason = "quarantined", result.reason[:100]
        else:
            job.status = "failed" if result.status == "failed" else "completed"
            job.last_error = result.reason[:100] if result.status != "ready" else None
            document.status, document.reason = result.status, result.reason[:100]
            document.warnings = result.warnings
            await self.session.execute(
                delete(DocumentPage).where(DocumentPage.document_id == document.id)
            )
            if result.status == "ready":
                for page in result.pages:
                    self.session.add(
                        DocumentPage(
                            document_id=document.id,
                            number=page.number,
                            text=page.text,
                            chunks=[
                                {"start": c.start, "end": c.end, "text": c.text}
                                for c in result.chunks
                                if c.page == page.number
                            ],
                        )
                    )
        await self.session.flush()
        return True
