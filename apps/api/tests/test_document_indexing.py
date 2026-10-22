import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import (
    DocumentVector,
    EmbeddingReservation,
    IndexJob,
    ResearchDocument,
)
from app.documents.embeddings import EmbeddingError
from app.documents.index_worker import IndexWorker
from app.documents.indexing import IndexRepository
from tests.test_document_repository import exercise
from tests.test_document_vectors import batch, seed


async def check_indexing(session, sessions, owner, doc):
    await seed(session, doc)
    repo = IndexRepository(session)
    with pytest.raises(AppError) as error:
        await repo.enqueue(owner.id, doc.id, accepted=False)
    assert error.value.status_code == 422
    with pytest.raises(AppError) as error:
        await repo.enqueue(uuid4(), doc.id, accepted=True)
    assert error.value.status_code == 404
    job_id = await repo.enqueue(owner.id, doc.id, accepted=True)
    assert await repo.enqueue(owner.id, doc.id, accepted=True) == job_id
    await session.commit()
    first = await repo.claim(10000)
    assert first is not None
    await session.commit()
    assert await repo.claim(10000) is None
    job = await session.get(IndexJob, job_id)
    job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    await session.commit()
    second = await repo.claim(10000)
    assert second is not None and second.token != first.token
    await session.commit()
    assert not await repo.finish(first, batch())
    assert await repo.finish(second, batch())
    await session.commit()
    assert await session.scalar(select(func.count()).select_from(DocumentVector)) >= 1
    reservations = list(
        await session.scalars(
            select(EmbeddingReservation).where(
                EmbeddingReservation.owner_id == owner.id
            )
        )
    )
    assert len(reservations) == 2
    assert (
        sum(r.reserved_tokens for r in reservations)
        == 2 * len(b"Graph attention method.") * 3
    )
    await session.delete(doc)
    await session.commit()
    assert await session.scalar(select(IndexJob).where(IndexJob.id == job_id)) is None
    assert (
        await session.scalar(
            select(func.count())
            .select_from(EmbeddingReservation)
            .where(EmbeddingReservation.owner_id == owner.id)
        )
        == 2
    )


def test_leases_disclosure_and_reservations(migrated_database_url):
    asyncio.run(exercise(migrated_database_url, check_indexing))


def test_quota_refuses_work_before_provider(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        await IndexRepository(session).enqueue(owner.id, doc.id, accepted=True)
        await session.commit()
        provider = AsyncMock()
        assert not await IndexWorker(sessions, provider, daily_limit=1).process_one()
        provider.embed.assert_not_called()
        async with sessions() as observer:
            job = await observer.scalar(select(IndexJob))
            assert job.status == "failed" and job.last_error == "document_exceeds_quota"
            assert (
                await observer.scalar(
                    select(func.count()).select_from(EmbeddingReservation)
                )
                == 0
            )

    asyncio.run(exercise(migrated_database_url, scenario))


@pytest.mark.parametrize("failure", [False, True])
def test_worker_commits_reservation_before_call_and_preserves_reader(
    migrated_database_url, failure
):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        await IndexRepository(session).enqueue(owner.id, doc.id, accepted=True)
        await session.commit()

        async def embed(inputs):
            async with sessions() as observer:
                assert (
                    await observer.scalar(
                        select(func.count()).select_from(EmbeddingReservation)
                    )
                    == 1
                )
            if failure:
                raise EmbeddingError("embedding_provider_unavailable", retry_after=60)
            return batch()

        provider = AsyncMock()
        provider.embed.side_effect = embed
        assert await IndexWorker(sessions, provider, daily_limit=10000).process_one()
        async with sessions() as observer:
            job = await observer.scalar(select(IndexJob))
            assert job.status == ("queued" if failure else "completed")
            assert (await observer.get(ResearchDocument, doc.id)).status == "ready"
            assert await observer.scalar(
                select(func.count()).select_from(DocumentVector)
            ) == (0 if failure else 1)

    asyncio.run(exercise(migrated_database_url, scenario))


def test_usage_budget_survives_failed_attempt(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        repo = IndexRepository(session)
        await repo.enqueue(owner.id, doc.id, accepted=True)
        await session.commit()
        limit = len(b"Graph attention method.") * 3
        lease = await repo.claim(limit)
        assert lease is not None
        await session.commit()
        assert await repo.finish(lease, None, error="fixture", retry_after=1)
        await session.commit()
        assert (
            await repo.claim(limit, datetime.now(UTC) + timedelta(seconds=40)) is None
        )
        job = await session.get(IndexJob, lease.job_id)
        assert job.last_error == "daily_quota"
        assert job.attempts == 1
        await session.delete(owner)
        await session.commit()
        assert (
            await session.scalar(select(func.count()).select_from(EmbeddingReservation))
            == 0
        )

    asyncio.run(exercise(migrated_database_url, scenario))


def test_cancelled_worker_leaves_recoverable_reservation(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        repo = IndexRepository(session)
        await repo.enqueue(owner.id, doc.id, accepted=True)
        await session.commit()
        entered = asyncio.Event()

        async def embed(inputs):
            entered.set()
            await asyncio.Event().wait()

        provider = AsyncMock()
        provider.embed.side_effect = embed
        task = asyncio.create_task(
            IndexWorker(sessions, provider, daily_limit=10000).process_one()
        )
        await asyncio.wait_for(entered.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        async with sessions() as observer:
            job = await observer.scalar(select(IndexJob))
            assert job.status == "processing"
            assert (
                await observer.scalar(
                    select(func.count()).select_from(EmbeddingReservation)
                )
                == 1
            )
            job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
            await observer.commit()
        assert await repo.claim(10000) is not None
        await session.commit()

    asyncio.run(exercise(migrated_database_url, scenario))


def test_worker_cli_status_and_disabled_guard(
    migrated_database_url, monkeypatch, capsys
):
    from app.core.config import Settings
    from app.documents import index_worker

    settings = Settings(
        _env_file=None,
        database_url=migrated_database_url,
        document_indexing_enabled=False,
        openai_api_key=None,
    )
    monkeypatch.setattr(index_worker, "Settings", lambda: settings)
    provider = AsyncMock()
    monkeypatch.setattr(index_worker, "create_embedder", provider)
    asyncio.run(index_worker.run(once=False, status=True))
    assert "{}" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="disabled"):
        asyncio.run(index_worker.run(once=True, status=False))
    provider.assert_not_called()


def test_cancellation_fences_active_worker_without_refund(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        repo = IndexRepository(session)
        await repo.enqueue(owner.id, doc.id, accepted=True)
        await session.commit()
        lease = await repo.claim(10000)
        assert lease is not None
        await session.commit()
        await repo.cancel(owner.id, doc.id)
        await session.commit()
        assert not await repo.renew(lease)
        assert not await repo.finish(lease, batch())
        assert (
            await session.scalar(select(func.count()).select_from(EmbeddingReservation))
            == 1
        )
        assert (
            await session.scalar(select(func.count()).select_from(DocumentVector)) == 0
        )

    asyncio.run(exercise(migrated_database_url, scenario))
