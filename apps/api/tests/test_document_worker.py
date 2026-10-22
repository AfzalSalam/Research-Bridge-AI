import asyncio
import hashlib
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy import delete, select

from app.db.models import AccountOwner, DocumentBlob, DocumentJob
from app.documents.blobs import BlobRepository
from app.documents.repository import DocumentRepository
from app.documents.scanner import ScanUnavailable
from app.documents.storage import StorageUnavailable
from app.documents.worker import DocumentWorker
from tests.test_document_repository import exercise
from tests.test_pdf_processing import pdf_bytes


def test_worker_scans_extracts_and_persists(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        content = pdf_bytes(
            ["The research evaluates a method using a held out test dataset."]
        )
        doc.sha256 = hashlib.sha256(content).hexdigest()
        await BlobRepository(session).register(doc, "research-documents")
        await DocumentRepository(session).enqueue(owner.id, doc.id)
        await session.commit()
        storage, scanner = AsyncMock(), AsyncMock()
        storage.download.return_value = content
        worker = DocumentWorker(sessions, storage, scanner)
        assert await worker.process_one()
        assert not await worker.process_one()
        scanner.scan.assert_awaited_once_with(content)
        await session.refresh(doc)
        assert doc.status == "ready"
        assert len(await DocumentRepository(session).pages(owner.id, doc.id)) == 1
        assert await BlobRepository(session).key(uuid4(), doc.id) is None

    asyncio.run(exercise(migrated_database_url, scenario))


def test_worker_rejects_changed_bytes_before_scanning(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await BlobRepository(session).register(doc, "research-documents")
        await DocumentRepository(session).enqueue(owner.id, doc.id)
        await session.commit()
        storage, scanner = AsyncMock(), AsyncMock()
        storage.download.return_value = b"modified"
        assert await DocumentWorker(sessions, storage, scanner).process_one()
        scanner.scan.assert_not_awaited()
        await session.refresh(doc)
        assert doc.status == "rejected" and doc.reason == "file_integrity_mismatch"

    asyncio.run(exercise(migrated_database_url, scenario))


def test_scanner_outage_keeps_file_quarantined(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        content = b"%PDF-fixture"
        doc.sha256 = hashlib.sha256(content).hexdigest()
        await BlobRepository(session).register(doc, "research-documents")
        await DocumentRepository(session).enqueue(owner.id, doc.id)
        await session.commit()
        storage, scanner = AsyncMock(), AsyncMock()
        storage.download.return_value = content
        scanner.scan.side_effect = ScanUnavailable()
        assert await DocumentWorker(sessions, storage, scanner).process_one()
        await session.refresh(doc)
        assert doc.status == "quarantined" and doc.reason == "scanner_unavailable"

    asyncio.run(exercise(migrated_database_url, scenario))


def test_cleanup_survives_account_deletion_and_retries(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        key = await BlobRepository(session).register(doc, "research-documents")
        await session.commit()
        await session.execute(delete(AccountOwner).where(AccountOwner.id == owner.id))
        await session.commit()
        blob = await session.scalar(select(DocumentBlob))
        assert blob is not None
        blob.available_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
        storage = AsyncMock()
        storage.delete.side_effect = StorageUnavailable()
        worker = DocumentWorker(sessions, storage, AsyncMock())
        assert await worker.cleanup_one()
        await session.refresh(blob)
        assert blob.status == "retained" and blob.attempts == 1
        blob.available_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
        storage.delete.side_effect = None
        assert await worker.cleanup_one()
        storage.delete.assert_awaited_with(key)
        assert await session.scalar(select(DocumentBlob)) is None

    asyncio.run(exercise(migrated_database_url, scenario))


def test_abandoned_upload_cleanup_has_grace_and_fencing(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        repo = BlobRepository(session)
        await repo.register(doc, "research-documents")
        now = datetime.now(UTC)
        assert await repo.claim_cleanup(now) is None
        first = await repo.claim_cleanup(now + timedelta(minutes=16))
        assert first is not None
        assert await repo.claim_cleanup(now + timedelta(minutes=17)) is None
        second = await repo.claim_cleanup(now + timedelta(minutes=22))
        assert second is not None
        assert not await repo.finish_cleanup(first, now=now + timedelta(minutes=22))
        assert await repo.finish_cleanup(second, now=now + timedelta(minutes=22))
        await session.refresh(doc)
        assert doc.reason == "upload_abandoned"

    asyncio.run(exercise(migrated_database_url, scenario))


def test_cancelled_worker_leaves_recoverable_claim(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await BlobRepository(session).register(doc, "research-documents")
        await DocumentRepository(session).enqueue(owner.id, doc.id)
        await session.commit()
        entered = asyncio.Event()

        async def blocked_download(key):
            entered.set()
            await asyncio.Event().wait()

        storage = AsyncMock()
        storage.download.side_effect = blocked_download
        task = asyncio.create_task(
            DocumentWorker(sessions, storage, AsyncMock()).process_one()
        )
        await entered.wait()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        job = await session.scalar(select(DocumentJob))
        assert job.status == "processing"
        lease = await DocumentRepository(session).claim(
            datetime.now(UTC) + timedelta(minutes=6)
        )
        assert lease is not None

    asyncio.run(exercise(migrated_database_url, scenario))
