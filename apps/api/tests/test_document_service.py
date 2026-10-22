import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.db.models import DocumentBlob, DocumentJob, ResearchDocument
from app.documents.service import DocumentService
from app.documents.storage import StorageUnavailable
from tests.test_document_repository import exercise


def test_upload_intent_committed_before_network_and_owner_delete(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        storage = AsyncMock()

        async def upload(key, content):
            async with sessions() as observer:
                row = await observer.get(ResearchDocument, key.document_id)
                assert row is not None and row.status == "uploading"
                assert (
                    await observer.scalar(
                        select(DocumentBlob).where(
                            DocumentBlob.document_id == key.document_id
                        )
                    )
                    is not None
                )

        storage.upload.side_effect = upload
        service = DocumentService(sessions, storage, "research-documents")
        id = await service.upload(owner.id, doc.paper_id, "paper.pdf", b"%PDF-fixture")
        async with sessions() as observer:
            row = await observer.get(ResearchDocument, id)
            assert row.status == "quarantined"
            assert (
                await observer.scalar(
                    select(DocumentJob).where(DocumentJob.document_id == id)
                )
                is not None
            )
        with pytest.raises(AppError) as error:
            await service.delete(uuid4(), id)
        assert error.value.status_code == 404
        await service.delete(owner.id, id)
        async with sessions() as observer:
            assert await observer.get(ResearchDocument, id) is None
            assert (
                await observer.scalar(
                    select(DocumentBlob).where(DocumentBlob.document_id == id)
                )
                is not None
            )

    asyncio.run(exercise(migrated_database_url, scenario))


def test_failed_upload_preserves_cleanup_intent(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        storage = AsyncMock()
        storage.upload.side_effect = StorageUnavailable()
        service = DocumentService(sessions, storage, "research-documents")
        with pytest.raises(AppError) as error:
            await service.upload(owner.id, doc.paper_id, "paper.pdf", b"%PDF-fixture")
        assert error.value.status_code == 503
        async with sessions() as observer:
            blob = await observer.scalar(select(DocumentBlob))
            assert blob is not None
            row = await observer.get(ResearchDocument, blob.document_id)
            assert row.status == "failed"
            assert await observer.scalar(select(DocumentJob)) is None

    asyncio.run(exercise(migrated_database_url, scenario))


def test_invalid_upload_never_reaches_storage(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        storage = AsyncMock()
        service = DocumentService(sessions, storage, "research-documents")
        with pytest.raises(AppError):
            await service.upload(owner.id, doc.paper_id, "paper.pdf", b"not pdf")
        with pytest.raises(AppError):
            await service.upload(uuid4(), doc.paper_id, "paper.pdf", b"%PDF-fixture")
        storage.upload.assert_not_awaited()

    asyncio.run(exercise(migrated_database_url, scenario))


def test_original_storage_failure_and_deletion_during_download(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        import hashlib

        from app.documents.blobs import BlobRepository

        content = b"%PDF-fixture"
        doc.status = "ready"
        doc.sha256 = hashlib.sha256(content).hexdigest()
        await BlobRepository(session).register(doc, "research-documents")
        await session.commit()
        storage = AsyncMock()
        service = DocumentService(sessions, storage, "research-documents")
        with pytest.raises(AppError) as error:
            await service.original(uuid4(), doc.id)
        assert error.value.status_code == 404
        storage.download.assert_not_awaited()
        storage.download.side_effect = StorageUnavailable()
        with pytest.raises(AppError) as error:
            await service.original(owner.id, doc.id)
        assert error.value.status_code == 503

        async def delete_while_loading(key):
            await service.delete(owner.id, doc.id)
            return content

        storage.download.side_effect = delete_while_loading
        with pytest.raises(AppError) as error:
            await service.original(owner.id, doc.id)
        assert error.value.status_code == 404

    asyncio.run(exercise(migrated_database_url, scenario))
