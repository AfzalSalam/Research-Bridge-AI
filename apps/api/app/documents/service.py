"""Upload intent commits before network writes so cleanup survives interruption."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models import AccountOwner, DocumentBlob, Paper, ResearchDocument
from app.db.models.enums import OwnerKind
from app.documents.blobs import BlobRepository
from app.documents.contracts import MAX_PDF_BYTES
from app.documents.repository import DocumentRepository
from app.documents.storage import DocumentStorage, StorageUnavailable


class DocumentService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        storage: DocumentStorage,
        bucket: str,
    ) -> None:
        self.sessions, self.storage, self.bucket = sessions, storage, bucket

    async def upload(
        self, owner_id: UUID, paper_id: UUID, filename: str, content: bytes
    ) -> UUID:
        if not content.startswith(b"%PDF-") or len(content) > MAX_PDF_BYTES:
            raise AppError(
                code="invalid_document",
                message="Upload a PDF of at most 20 MiB.",
                status_code=422,
            )
        filename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not filename or len(filename) > 255 or any(ord(c) < 32 for c in filename):
            raise AppError(
                code="invalid_filename",
                message="Use a valid PDF filename.",
                status_code=422,
            )
        async with self.sessions() as session:
            # Serializes quota checks for one owner and conflicts with account deletion.
            owner = await session.scalar(
                select(AccountOwner)
                .where(AccountOwner.id == owner_id)
                .with_for_update()
            )
            if owner is None or owner.kind != OwnerKind.AUTHENTICATED:
                raise AppError(
                    code="account_not_found",
                    message="Account not found.",
                    status_code=404,
                )
            recent = await session.scalar(
                select(func.count())
                .select_from(DocumentBlob)
                .where(
                    DocumentBlob.owner_id == owner_id,
                    DocumentBlob.created_at >= datetime.now(UTC) - timedelta(minutes=1),
                )
            )
            if recent is not None and recent >= 5:
                raise AppError(
                    code="upload_rate_limited",
                    message="Wait a minute before uploading another paper.",
                    status_code=429,
                )
            if await session.get(Paper, paper_id) is None:
                raise AppError(
                    code="paper_not_found", message="Paper not found.", status_code=404
                )
            count, size = (
                await session.execute(
                    select(
                        func.count(),
                        func.coalesce(func.sum(ResearchDocument.byte_size), 0),
                    ).where(ResearchDocument.owner_id == owner_id)
                )
            ).one()
            if count >= 100 or size + len(content) > 200 * 1024 * 1024:
                raise AppError(
                    code="document_quota_exceeded",
                    message="Remove a document before uploading another.",
                    status_code=409,
                )
            document = ResearchDocument(
                id=uuid4(),
                owner_id=owner_id,
                paper_id=paper_id,
                filename=filename,
                byte_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
            )
            session.add(document)
            await session.flush()
            key = await BlobRepository(session).register(document, self.bucket)
            await session.commit()
        try:
            async with asyncio.timeout(120):
                await self.storage.upload(key, content)
        except (StorageUnavailable, TimeoutError) as exc:
            async with self.sessions() as session:
                row = await session.get(ResearchDocument, key.document_id)
                if row is not None and row.status == "uploading":
                    row.status, row.reason = "failed", "upload_not_confirmed"
                    await session.commit()
            raise AppError(
                code="document_upload_failed",
                message="Upload could not be confirmed. Please try again later.",
                status_code=503,
            ) from exc
        async with self.sessions() as session:
            await DocumentRepository(session).enqueue(owner_id, key.document_id)
            await session.commit()
        return key.document_id

    async def original(self, owner_id: UUID, document_id: UUID) -> bytes:
        async with self.sessions() as session:
            row = await DocumentRepository(session).owned(owner_id, document_id)
            if row.status != "ready":
                raise AppError(
                    code="document_not_ready",
                    message="This PDF is not ready.",
                    status_code=409,
                )
            expected_hash = row.sha256
            key = await BlobRepository(session).key(owner_id, document_id)
        if key is None:
            raise AppError(
                code="document_file_unavailable",
                message="PDF temporarily unavailable.",
                status_code=503,
            )
        try:
            async with asyncio.timeout(60):
                content = await self.storage.download(key)
        except (StorageUnavailable, TimeoutError) as exc:
            raise AppError(
                code="document_file_unavailable",
                message="PDF temporarily unavailable.",
                status_code=503,
            ) from exc
        if (
            len(content) > MAX_PDF_BYTES
            or not content.startswith(b"%PDF-")
            or hashlib.sha256(content).hexdigest() != expected_hash
        ):
            raise AppError(
                code="document_integrity_failed",
                message="This file no longer matches the scanned PDF. Upload it again.",
                status_code=409,
            )
        # A deletion during the external request must prevent returning the file.
        async with self.sessions() as session:
            row = await DocumentRepository(session).owned(owner_id, document_id)
            if row.status != "ready" or row.sha256 != expected_hash:
                raise AppError(
                    code="document_not_ready",
                    message="This PDF is not ready.",
                    status_code=409,
                )
        return content

    async def delete(self, owner_id: UUID, document_id: UUID) -> None:
        async with self.sessions() as session:
            document = await DocumentRepository(session).owned(owner_id, document_id)
            await session.delete(document)
            await session.commit()
