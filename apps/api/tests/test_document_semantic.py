import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import EmbeddingReservation, IndexJob
from app.documents.embeddings import EmbeddingError
from app.documents.indexing import DISCLOSURE_VERSION
from app.documents.semantic import (
    QUERY_DISCLOSURE_VERSION,
    SemanticQuery,
    SemanticSearch,
    reserve_query,
)
from app.documents.vectors import VectorRepository
from tests.test_document_repository import exercise
from tests.test_document_vectors import batch, seed


def request(**changes):
    return SemanticQuery(
        **dict(
            {
                "query": "graph",
                "accepted": True,
                "disclosure_version": QUERY_DISCLOSURE_VERSION,
            },
            **changes,
        )
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"accepted": False},
        {"disclosure_version": "old"},
        {"query": "   "},
        {"query": "x" * 501},
    ],
)
def test_query_requires_current_consent_and_bounded_text(changes):
    with pytest.raises(ValidationError):
        request(**changes)


async def check_query_budget(session, sessions, owner, doc):
    page, chunk = await seed(session, doc)

    async def used():
        return int(
            await session.scalar(
                select(
                    func.coalesce(func.sum(EmbeddingReservation.reserved_tokens), 0)
                ).where(EmbeddingReservation.owner_id == owner.id)
            )
        )

    before = await used()
    with pytest.raises(AppError) as missing:
        await reserve_query(session, owner.id, doc.id, request(), daily_limit=1000000)
    assert missing.value.code == "paper_index_required"
    assert await used() == before
    job = IndexJob(
        document_id=doc.id,
        status="completed",
        available_at=datetime.now(UTC),
        disclosure_version=DISCLOSURE_VERSION,
        accepted_at=datetime.now(UTC),
    )
    session.add(job)
    await VectorRepository(session).replace(owner.id, doc.id, [chunk], batch())
    await session.commit()
    with pytest.raises(AppError) as denied:
        await reserve_query(session, uuid4(), doc.id, request(), daily_limit=1000000)
    assert denied.value.status_code == 404
    cost = len(request().query.encode()) * 3
    await reserve_query(session, owner.id, doc.id, request(), daily_limit=before + cost)
    await session.commit()
    assert await used() == before + cost
    with pytest.raises(AppError) as exhausted:
        await reserve_query(
            session, owner.id, doc.id, request(), daily_limit=before + cost
        )
    assert exhausted.value.status_code == 429
    assert await used() == before + cost
    await session.commit()

    class Provider:
        calls = 0
        mode = "success"

        async def embed(self, texts):
            self.calls += 1
            assert texts == ["graph"]
            async with sessions() as observer:
                reserved = await observer.scalar(
                    select(func.sum(EmbeddingReservation.reserved_tokens)).where(
                        EmbeddingReservation.owner_id == owner.id
                    )
                )
                assert reserved == before + cost * (1 + self.calls)
            if self.mode == "timeout":
                raise EmbeddingError("provider_timeout")
            if self.mode == "cancel":
                raise asyncio.CancelledError()
            if self.mode == "invalid":
                return type(batch())("wrong-model", 1, ((1.0,),), 1)
            return batch()

    provider = Provider()
    service = SemanticSearch(sessions, provider, enabled=False, daily_limit=1000000)
    with pytest.raises(AppError) as disabled:
        await service.search(owner.id, doc.id, request())
    assert disabled.value.status_code == 503
    assert provider.calls == 0
    service.enabled = True
    if session.get_bind().dialect.name == "postgresql":
        result = await service.search(owner.id, doc.id, request())
        assert result.passages == [chunk]
        provider.mode = "timeout"
        with pytest.raises(EmbeddingError):
            await service.search(owner.id, doc.id, request())
        assert await used() == before + cost * 3
        provider.mode = "invalid"
        with pytest.raises(EmbeddingError) as invalid:
            await service.search(owner.id, doc.id, request())
        assert invalid.value.code == "invalid_embedding_response"
        provider.mode = "cancel"
        with pytest.raises(asyncio.CancelledError):
            await service.search(owner.id, doc.id, request())
        assert await used() == before + cost * 5
        with pytest.raises(AppError) as other_account:
            await service.search(uuid4(), doc.id, request())
        assert other_account.value.status_code == 404
        assert provider.calls == 4
    else:
        with pytest.raises(AppError) as unavailable:
            await service.search(owner.id, doc.id, request())
        assert unavailable.value.status_code == 503
        assert provider.calls == 0


def test_budget_ownership_index_and_configuration(migrated_database_url):
    asyncio.run(exercise(migrated_database_url, check_query_budget))
