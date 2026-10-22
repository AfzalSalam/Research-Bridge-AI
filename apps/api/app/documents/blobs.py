"""Durable object cleanup with no dependency on a surviving account row."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.documents import DocumentBlob, ResearchDocument
from app.documents.storage import ObjectKey


@dataclass(frozen=True)
class CleanupLease:
    id: UUID
    token: UUID
    key: ObjectKey


class BlobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, document: ResearchDocument, bucket: str) -> ObjectKey:
        # Commit this together with the new document BEFORE the first storage write.
        key = ObjectKey(document.owner_id, document.id, bucket)
        self.session.add(
            DocumentBlob(
                owner_id=document.owner_id,
                document_id=document.id,
                bucket=bucket,
                available_at=datetime.now(UTC) + timedelta(minutes=15),
            )
        )
        await self.session.flush()
        return key

    async def key(self, owner: UUID, document: UUID) -> ObjectKey | None:
        blob = await self.session.scalar(
            select(DocumentBlob).where(
                DocumentBlob.owner_id == owner,
                DocumentBlob.document_id == document,
                DocumentBlob.status == "retained",
            )
        )
        return ObjectKey(blob.owner_id, blob.document_id, blob.bucket) if blob else None

    async def claim_cleanup(self, now: datetime | None = None) -> CleanupLease | None:
        now = now or datetime.now(UTC)
        # A dead upload never becomes readable; the ledger still knows its object key.
        await self.session.execute(
            update(ResearchDocument)
            .where(
                ResearchDocument.status == "uploading",
                ResearchDocument.created_at < now - timedelta(minutes=15),
            )
            .values(status="failed", reason="upload_abandoned")
            .execution_options(synchronize_session="fetch")
        )
        live_document = exists(
            select(ResearchDocument.id).where(
                ResearchDocument.id == DocumentBlob.document_id,
                ResearchDocument.status.not_in(["failed", "rejected", "unsupported"]),
            )
        )
        while True:
            blob = await self.session.scalar(
                select(DocumentBlob)
                .where(
                    ~live_document,
                    DocumentBlob.available_at <= now,
                    or_(
                        DocumentBlob.status == "retained",
                        (DocumentBlob.status == "deleting")
                        & (DocumentBlob.lease_until <= now),
                    ),
                )
                .order_by(DocumentBlob.available_at, DocumentBlob.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if blob is None:
                return None
            if blob.attempts >= 10:
                blob.status, blob.last_error = "failed", "cleanup_retry_limit"
                blob.lease_until, blob.lease_token = None, None
                await self.session.flush()
                continue
            blob.status = "deleting"
            blob.attempts += 1
            blob.lease_token = uuid4()
            blob.lease_until = now + timedelta(minutes=5)
            await self.session.flush()
            return CleanupLease(
                blob.id,
                blob.lease_token,
                ObjectKey(blob.owner_id, blob.document_id, blob.bucket),
            )

    async def finish_cleanup(
        self,
        lease: CleanupLease,
        *,
        error: str | None = None,
        retry_after: int = 30,
        now: datetime | None = None,
    ) -> bool:
        now = now or datetime.now(UTC)
        blob = await self.session.scalar(
            select(DocumentBlob)
            .where(
                DocumentBlob.id == lease.id,
                DocumentBlob.lease_token == lease.token,
                DocumentBlob.status == "deleting",
                DocumentBlob.lease_until > now,
            )
            .with_for_update()
        )
        if blob is None:
            return False
        if error is None:
            await self.session.execute(
                delete(DocumentBlob).where(DocumentBlob.id == blob.id)
            )
        else:
            blob.status = "failed" if blob.attempts >= 10 else "retained"
            blob.last_error = error[:100]
            blob.lease_token, blob.lease_until = None, None
            blob.available_at = now + timedelta(
                seconds=max(min(retry_after, 3600), min(30 * 2**blob.attempts, 3600))
            )
        await self.session.flush()
        return True
