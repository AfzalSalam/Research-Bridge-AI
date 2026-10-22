import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import AppError
from app.db.models import (
    AccountOwner,
    DocumentJob,
    DocumentPage,
    Paper,
    ResearchDocument,
)
from app.db.models.enums import EvidenceStrength, OwnerKind
from app.documents.contracts import PdfChunk, PdfExtraction, PdfPage
from app.documents.repository import DocumentRepository

NOW = datetime(2026, 10, 12, tzinfo=UTC)
READY = PdfExtraction(
    status="ready",
    reason="extracted",
    pages=[PdfPage(number=1, text="Evidence")],
    chunks=[PdfChunk(page=1, start=0, end=8, text="Evidence")],
)


async def exercise(url, scenario):
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            await session.execute(text("PRAGMA foreign_keys=ON"))
            owner = AccountOwner(
                kind=OwnerKind.AUTHENTICATED, auth_subject=str(uuid4())
            )
            paper = Paper(
                title="Fixture",
                normalized_title="fixture",
                publication_year=2026,
                evidence_strength=list(EvidenceStrength)[0],
                primary_source_url="https://example.org/paper",
                last_verified_at=NOW,
            )
            session.add_all([owner, paper])
            await session.flush()
            doc = ResearchDocument(
                owner_id=owner.id,
                paper_id=paper.id,
                filename="paper.pdf",
                byte_size=100,
                sha256="a" * 64,
            )
            session.add(doc)
            await session.commit()
            await scenario(session, sessions, owner, doc)
    finally:
        await engine.dispose()


def test_owner_isolation_and_quarantine(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        repo = DocumentRepository(session)
        for operation in (repo.owned, repo.pages, repo.enqueue):
            with pytest.raises(AppError) as error:
                await operation(uuid4(), doc.id)
            assert error.value.status_code == 404
        with pytest.raises(AppError) as error:
            await repo.pages(owner.id, doc.id)
        assert error.value.status_code == 409
        await repo.enqueue(owner.id, doc.id)
        with pytest.raises(AppError) as error:
            await repo.enqueue(owner.id, doc.id)
        assert error.value.status_code == 409

    asyncio.run(exercise(migrated_database_url, scenario))


def test_persisted_claim_and_fenced_crash_recovery(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        repo = DocumentRepository(session)
        await repo.enqueue(owner.id, doc.id)
        await session.commit()
        now = datetime.now(UTC) + timedelta(seconds=1)
        first = await repo.claim(now)
        assert first is not None
        await session.commit()
        async with sessions() as restarted:
            worker = DocumentRepository(restarted)
            assert await worker.claim(now + timedelta(minutes=1)) is None
            second = await worker.claim(now + timedelta(minutes=6))
            assert second is not None and second.token != first.token
            await restarted.commit()
            assert not await worker.finish(first, READY, now + timedelta(minutes=6))
            assert await worker.finish(second, READY, now + timedelta(minutes=7))
            await restarted.commit()
            pages = await worker.pages(owner.id, doc.id)
            assert [(p.number, p.text, p.chunks) for p in pages] == [
                (1, "Evidence", [{"start": 0, "end": 8, "text": "Evidence"}])
            ]
            assert not await worker.finish(second, READY, now + timedelta(minutes=7))

    asyncio.run(exercise(migrated_database_url, scenario))


def test_transient_failures_are_bounded(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        repo = DocumentRepository(session)
        await repo.enqueue(owner.id, doc.id)
        now = datetime.now(UTC) + timedelta(seconds=1)
        for _attempt in range(3):
            lease = await repo.claim(now)
            assert lease is not None
            assert await repo.finish(
                lease, PdfExtraction(status="failed", reason="scanner_unavailable"), now
            )
            assert await repo.claim(now) is None
            now += timedelta(minutes=1)
        await session.refresh(doc)
        assert doc.status == "failed"
        assert await repo.claim(now + timedelta(days=1)) is None
        assert list(await session.scalars(select(DocumentPage))) == []

    asyncio.run(exercise(migrated_database_url, scenario))


def test_repeated_worker_crashes_stop_and_deletion_cascades(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        repo = DocumentRepository(session)
        await repo.enqueue(owner.id, doc.id)
        now = datetime.now(UTC) + timedelta(seconds=1)
        for _attempt in range(3):
            lease = await repo.claim(now)
            assert lease is not None
            now += timedelta(minutes=6)
        assert await repo.claim(now) is None
        await session.refresh(doc)
        assert doc.status == "failed" and doc.reason == "retry_limit"
        await session.execute(delete(AccountOwner).where(AccountOwner.id == owner.id))
        await session.commit()
        assert await session.scalar(select(ResearchDocument)) is None
        assert await session.scalar(select(DocumentJob)) is None
        assert not await repo.finish(lease, READY, now)

    asyncio.run(exercise(migrated_database_url, scenario))


def test_unsupported_document_is_terminal(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        repo = DocumentRepository(session)
        await repo.enqueue(owner.id, doc.id)
        now = datetime.now(UTC) + timedelta(seconds=1)
        lease = await repo.claim(now)
        assert lease is not None
        assert await repo.finish(
            lease,
            PdfExtraction(status="unsupported", reason="no_extractable_text"),
            now,
        )
        assert await repo.claim(now + timedelta(days=1)) is None
        with pytest.raises(AppError):
            await repo.pages(owner.id, doc.id)

    asyncio.run(exercise(migrated_database_url, scenario))
