import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx2
import pytest

from app.clients.openalex import OpenAlexClient
from app.providers.base import (
    AcademicProviderError,
    ClassifiedDiscoveryQuery,
    DiscoveryQueryKind,
    ProviderFailureKind,
)

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "openalex" / "works-representative.json"
)
FIXED_TIME = datetime(2026, 8, 1, 15, 0, tzinfo=UTC)


def fixture_payload() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def text_query() -> ClassifiedDiscoveryQuery:
    return ClassifiedDiscoveryQuery(
        kind=DiscoveryQueryKind.TEXT,
        value="clinical AI",
        display_value="clinical AI",
    )


def build_client(
    handler: httpx2.AsyncBaseTransport,
    *,
    api_key: str | None = "private-test-key",
    sleep: object | None = None,
) -> tuple[httpx2.AsyncClient, OpenAlexClient]:
    http_client = httpx2.AsyncClient(
        base_url="https://api.openalex.org", transport=handler
    )

    async def default_sleep(_: float) -> None:
        return None

    provider = OpenAlexClient(
        http_client,
        api_key=api_key,
        max_attempts=3,
        backoff_base_seconds=0.25,
        backoff_cap_seconds=2,
        sleep=sleep if callable(sleep) else default_sleep,
        clock=lambda: FIXED_TIME,
    )
    return http_client, provider


def test_text_search_builds_a_bounded_server_authenticated_request() -> None:
    seen: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(
            200,
            json={**fixture_payload(), "results": fixture_payload()["results"][:2]},
            headers={"X-RateLimit-Remaining": "97"},
        )

    async def run() -> None:
        http_client, provider = build_client(httpx2.MockTransport(handler))
        try:
            result = await provider.search_papers(text_query(), 12)
        finally:
            await http_client.aclose()
        assert len(result.records) == 2
        assert result.rate_limit.remaining == 97
        assert result.access_mode == "api-key"

    asyncio.run(run())
    assert seen[0].url.path == "/works"
    assert seen[0].url.params["search"] == "clinical AI"
    assert seen[0].url.params["per_page"] == "12"
    assert seen[0].url.params["api_key"] == "private-test-key"


def test_transient_failure_retries_with_bounded_backoff() -> None:
    attempts = 0
    delays: list[float] = []

    async def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx2.Response(503)
        return httpx2.Response(200, json={"meta": {"count": 0}, "results": []})

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    async def run() -> None:
        http_client, provider = build_client(
            httpx2.MockTransport(handler), sleep=record_sleep
        )
        try:
            result = await provider.search_papers(text_query(), 5)
        finally:
            await http_client.aclose()
        assert result.records == ()

    asyncio.run(run())
    assert attempts == 3
    assert delays == [0.25, 0.5]


def test_doi_lookup_stays_on_the_fixed_origin_and_encodes_the_identifier() -> None:
    seen: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        record = fixture_payload()["results"][0]
        return httpx2.Response(200, json=record)

    query = ClassifiedDiscoveryQuery(
        kind=DiscoveryQueryKind.DOI,
        value="10.1234/rbai.2026.001",
        display_value="10.1234/rbai.2026.001",
    )

    async def run() -> None:
        http_client, provider = build_client(httpx2.MockTransport(handler))
        try:
            result = await provider.search_papers(query, 1)
        finally:
            await http_client.aclose()
        assert len(result.records) == 1

    asyncio.run(run())
    assert seen[0].url.host == "api.openalex.org"
    assert seen[0].url.path == "/works/doi:10.1234/rbai.2026.001"
    assert b"%2F" in seen[0].url.raw_path


def test_transport_failure_exhausts_the_retry_budget_without_leaking_a_url() -> None:
    attempts = 0

    async def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        raise httpx2.ConnectTimeout("provider URL omitted", request=request)

    async def run() -> AcademicProviderError:
        http_client, provider = build_client(httpx2.MockTransport(handler))
        try:
            with pytest.raises(AcademicProviderError) as captured:
                await provider.search_papers(text_query(), 5)
            return captured.value
        finally:
            await http_client.aclose()

    error = asyncio.run(run())
    assert attempts == 3
    assert error.kind is ProviderFailureKind.NETWORK
    assert "api.openalex.org" not in str(error)
    assert "private-test-key" not in str(error)


def test_invalid_json_is_a_non_retryable_provider_contract_failure() -> None:
    attempts = 0

    async def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        return httpx2.Response(200, content=b"not-json")

    async def run() -> AcademicProviderError:
        http_client, provider = build_client(httpx2.MockTransport(handler))
        try:
            with pytest.raises(AcademicProviderError) as captured:
                await provider.search_papers(text_query(), 5)
            return captured.value
        finally:
            await http_client.aclose()

    error = asyncio.run(run())
    assert attempts == 1
    assert error.kind is ProviderFailureKind.INVALID_RESPONSE
    assert error.retryable is False


def test_rate_limit_is_not_retried_and_secret_is_not_in_the_error() -> None:
    attempts = 0

    async def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        return httpx2.Response(
            429,
            json={"error": "rate limit"},
            headers={"X-RateLimit-Reset": "120"},
        )

    async def run() -> AcademicProviderError:
        http_client, provider = build_client(httpx2.MockTransport(handler))
        try:
            with pytest.raises(AcademicProviderError) as captured:
                await provider.search_papers(text_query(), 5)
            return captured.value
        finally:
            await http_client.aclose()

    error = asyncio.run(run())
    assert attempts == 1
    assert error.kind is ProviderFailureKind.RATE_LIMIT
    assert error.retry_after_seconds == 120
    assert "private-test-key" not in str(error)


def test_exact_not_found_is_an_empty_result() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        assert "W1000000999" in request.url.path
        return httpx2.Response(404, json={"error": "not found"})

    query = ClassifiedDiscoveryQuery(
        kind=DiscoveryQueryKind.OPENALEX_ID,
        value="W1000000999",
        display_value="W1000000999",
    )

    async def run() -> None:
        http_client, provider = build_client(
            httpx2.MockTransport(handler), api_key=None
        )
        try:
            result = await provider.search_papers(query, 1)
        finally:
            await http_client.aclose()
        assert result.records == ()
        assert result.access_mode == "limited-anonymous"

    asyncio.run(run())
