import asyncio
import json
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx2
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import DocumentPage, DocumentVector, EmbeddingReservation, IndexJob
from app.documents.embeddings import EmbeddingError
from app.documents.gemini import GeminiEmbeddings
from app.documents.index_worker import IndexWorker
from app.documents.indexing import IndexRepository
from app.documents.providers import GEMINI, OPENAI, configured, policy
from app.documents.semantic import SemanticQuery, SemanticSearch, reserve_query
from tests.test_document_repository import exercise
from tests.test_document_vectors import batch, seed


def settings():
    return Settings(
        _env_file=None,
        gemini_api_key=SecretStr("fixture-key"),
        document_embedding_provider="gemini",
    )


@pytest.mark.parametrize(
    "query,prefix", [(False, GEMINI.document_prefix), (True, GEMINI.query_prefix)]
)
def test_gemini_transport_and_normalization(query, prefix):
    async def run():
        def handler(request):
            assert request.url.host == "generativelanguage.googleapis.com"
            assert request.url.query == b""
            assert request.headers["x-goog-api-key"] == "fixture-key"
            payload = json.loads(request.content)
            assert payload["content"] == {"parts": [{"text": prefix + "test"}]}
            assert payload["outputDimensionality"] == 1536
            return httpx2.Response(
                200, json={"embedding": {"values": [2.0] + [0.0] * 1535}}
            )

        client = GeminiEmbeddings(
            settings(), query=query, transport=httpx2.MockTransport(handler)
        )
        try:
            result = await client.embed(["test"])
            assert result.model == GEMINI.model and result.vectors[0][0] == 1
            assert result.dimensions == 1536
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "values", [[0.0] * 1536, [1.0] * 1535, ["bad"] * 1536, [float("inf")] * 1536]
)
def test_gemini_rejects_invalid_vectors(values):
    async def run():
        client = GeminiEmbeddings(settings())
        try:
            with pytest.raises(EmbeddingError, match="invalid_embedding_response"):
                client.validate(
                    json.dumps({"embedding": {"values": values}}).encode(), 1
                )
        finally:
            await client.aclose()

    asyncio.run(run())


def test_gemini_no_aggregation_and_no_redirect_or_secret_error():
    async def run():
        handler = AsyncMock(
            return_value=httpx2.Response(
                302, headers={"location": "https://example.org"}, text="fixture-key"
            )
        )
        client = GeminiEmbeddings(settings(), transport=httpx2.MockTransport(handler))
        try:
            with pytest.raises(EmbeddingError, match="invalid_embedding_input"):
                await client.embed(["first", "second"])
            handler.assert_not_called()
            with pytest.raises(EmbeddingError) as error:
                await client.embed(["test"])
            assert str(error.value) == "embedding_provider_refused"
            assert handler.call_count == 1
        finally:
            await client.aclose()

    asyncio.run(run())


def test_gemini_rate_limit_is_bounded():
    async def run():
        handler = AsyncMock(
            return_value=httpx2.Response(429, headers={"retry-after": "60"})
        )
        sleep = AsyncMock()
        client = GeminiEmbeddings(
            settings(), transport=httpx2.MockTransport(handler), sleep=sleep
        )
        try:
            with pytest.raises(EmbeddingError) as error:
                await client.embed(["test"])
            assert error.value.retry_after == 60
            assert handler.call_count == 1
            sleep.assert_not_called()
        finally:
            await client.aclose()

    asyncio.run(run())


def test_provider_selection_is_explicit():
    assert policy(settings()) == GEMINI and configured(settings())
    assert policy(Settings(_env_file=None, gemini_api_key=SecretStr("test"))) == OPENAI
    assert not configured(
        Settings(_env_file=None, document_embedding_provider="gemini")
    )


async def check_gemini_binding(session, sessions, owner, doc):
    await seed(session, doc)
    old = IndexRepository(session)
    await old.enqueue(owner.id, doc.id, accepted=True)
    await session.commit()
    gemini = IndexRepository(session, GEMINI)
    # A Gemini worker must never claim a paper consented only for OpenAI.
    assert await gemini.claim(10000) is None
    lease = await old.claim(10000)
    assert lease
    await session.commit()
    await gemini.enqueue(owner.id, doc.id, accepted=True)
    await session.commit()
    assert not await old.finish(lease, batch())
    provider = AsyncMock()
    provider.embed.return_value = replace(batch(), model=GEMINI.model)
    assert await IndexWorker(
        sessions, provider, daily_limit=10000, embedding_policy=GEMINI
    ).process_one()
    await session.refresh(doc)
    job = await session.scalar(
        select(IndexJob)
        .where(IndexJob.document_id == doc.id)
        .execution_options(populate_existing=True)
    )
    assert job.status == "completed" and job.disclosure_version == GEMINI.disclosure
    assert (
        await session.scalar(
            select(DocumentVector.model)
            .join_from(DocumentVector, DocumentPage)
            .where(DocumentPage.document_id == doc.id)
        )
        == GEMINI.model
    )
    reservations = list(
        await session.scalars(
            select(EmbeddingReservation).where(
                EmbeddingReservation.owner_id == owner.id
            )
        )
    )
    assert (
        sum(r.reserved_tokens for r in reservations)
        == (len(b"Graph attention method.") * 2 + len(GEMINI.document_prefix.encode()))
        * 3
    )
    request = SemanticQuery(
        query="graph", accepted=True, disclosure_version=GEMINI.query_disclosure
    )
    before = sum(r.reserved_tokens for r in reservations)
    await reserve_query(session, owner.id, doc.id, request, daily_limit=10000)
    await session.commit()
    assert (
        await session.scalar(
            select(func.sum(EmbeddingReservation.reserved_tokens)).where(
                EmbeddingReservation.owner_id == owner.id
            )
        )
        == before + len((GEMINI.query_prefix + "graph").encode()) * 3
    )
    provider.reset_mock()
    search = SemanticSearch(
        sessions, provider, enabled=True, daily_limit=10000, embedding_policy=GEMINI
    )
    with pytest.raises(AppError, match="Refresh"):
        await search.search(
            owner.id,
            doc.id,
            SemanticQuery(
                query="graph", accepted=True, disclosure_version=OPENAI.query_disclosure
            ),
        )
    provider.embed.assert_not_called()
    if session.get_bind().dialect.name == "postgresql":
        result = await search.search(owner.id, doc.id, request)
        assert result.passages and result.passages[0].page == 1
        provider.embed.return_value = batch()  # Wrong model must fail before retrieval.
        with pytest.raises(EmbeddingError, match="invalid_embedding_response"):
            await search.search(owner.id, doc.id, request)


def test_gemini_consent_lease_model_and_quota_binding(migrated_database_url):
    asyncio.run(exercise(migrated_database_url, check_gemini_binding))
