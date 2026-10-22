"""Run with python -m app.documents.worker; credentials remain server-side."""

import argparse
import asyncio
import hashlib
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.models.documents import DocumentBlob, DocumentJob
from app.db.session import create_database
from app.documents.blobs import BlobRepository
from app.documents.contracts import PdfExtraction
from app.documents.processing import process_pdf
from app.documents.repository import DocumentRepository
from app.documents.scanner import ClamAvScanner, DocumentScanner
from app.documents.storage import (
    DocumentStorage,
    StorageUnavailable,
    SupabaseDocumentStorage,
)

logger = logging.getLogger(__name__)


class DocumentWorker:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        storage: DocumentStorage,
        scanner: DocumentScanner,
    ) -> None:
        self.sessions, self.storage, self.scanner = sessions, storage, scanner

    async def process_one(self) -> bool:
        async with self.sessions() as session:
            lease = await DocumentRepository(session).claim()
            key = (
                await BlobRepository(session).key(lease.owner_id, lease.document_id)
                if lease
                else None
            )
            await session.commit()
        if lease is None:
            return False
        retry_after = 0
        if key is None:
            result = PdfExtraction(status="failed", reason="storage_record_missing")
        else:
            try:
                content = await self.storage.download(key)
                if hashlib.sha256(content).hexdigest() != lease.sha256:
                    result = PdfExtraction(
                        status="rejected", reason="file_integrity_mismatch"
                    )
                else:
                    result = await process_pdf(content, self.scanner)
            except StorageUnavailable as exc:
                result = PdfExtraction(status="failed", reason=exc.code)
                retry_after = exc.retry_after
            except OSError:
                result = PdfExtraction(status="failed", reason="processing_unavailable")
        async with self.sessions() as session:
            accepted = await DocumentRepository(session).finish(
                lease, result, retry_after=retry_after
            )
            await session.commit()
        logger.info(
            "document_job completed accepted=%s status=%s", accepted, result.status
        )
        return True

    async def cleanup_one(self) -> bool:
        async with self.sessions() as session:
            lease = await BlobRepository(session).claim_cleanup()
            await session.commit()
        if lease is None:
            return False
        error, retry_after = None, 30
        try:
            await self.storage.delete(lease.key)
        except StorageUnavailable as exc:
            error, retry_after = exc.code, exc.retry_after
        async with self.sessions() as session:
            accepted = await BlobRepository(session).finish_cleanup(
                lease, error=error, retry_after=retry_after
            )
            await session.commit()
        logger.info(
            "document_cleanup completed accepted=%s success=%s", accepted, error is None
        )
        return True


async def run(*, once: bool, status: bool) -> None:
    settings = Settings()
    database = create_database(settings)
    try:
        if status:
            async with database.session_factory() as session:
                for model in (DocumentJob, DocumentBlob):
                    counts = await session.execute(
                        select(model.status, func.count()).group_by(model.status)
                    )
                    print(
                        model.__tablename__, {state: count for state, count in counts}
                    )
            return
        if not settings.document_scanner_host:
            raise SystemExit("Set DOCUMENT_SCANNER_HOST before starting the worker.")
        try:
            storage = SupabaseDocumentStorage(settings)
        except StorageUnavailable:
            raise SystemExit(
                "Configure private Supabase Storage before starting the worker."
            ) from None
        try:
            worker = DocumentWorker(
                database.session_factory,
                storage,
                ClamAvScanner(
                    settings.document_scanner_host, settings.document_scanner_port
                ),
            )
            while True:
                cleaned = await worker.cleanup_one()
                processed = await worker.process_one()
                if once:
                    break
                if not cleaned and not processed:
                    await asyncio.sleep(5)
        finally:
            await storage.aclose()
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Private PDF processing and cleanup worker"
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show aggregate job counts without private content",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(once=args.once, status=args.status))
