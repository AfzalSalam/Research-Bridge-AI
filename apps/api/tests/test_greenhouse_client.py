import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx2
import pytest

from app.clients.greenhouse import GreenhouseClient
from app.providers.opportunities import (
    OPPORTUNITY_SOURCES,
    OpportunityProviderError,
    OpportunityProviderFailureKind,
)

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "greenhouse" / "jobs-representative.json"
)
FIXED_TIME = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def fixture_payload() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def build_client(
    transport: httpx2.AsyncBaseTransport,
    *,
    sleep: object | None = None,
) -> tuple[httpx2.AsyncClient, GreenhouseClient]:
    http_client = httpx2.AsyncClient(
        base_url="https://boards-api.greenhouse.io", transport=transport
    )

    async def default_sleep(_: float) -> None:
        return None

    provider = GreenhouseClient(
        http_client,
        max_attempts=3,
        backoff_base_seconds=0.25,
        backoff_cap_seconds=2,
        sleep=sleep if callable(sleep) else default_sleep,
        clock=lambda: FIXED_TIME,
    )
    return http_client, provider


def test_public_board_request_is_fixed_origin_bounded_and_individually_validated() -> (
    None
):
    seen: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=fixture_payload())

    async def run() -> None:
        client, provider = build_client(httpx2.MockTransport(handler))
        try:
            result = await provider.fetch_board(
                OPPORTUNITY_SOURCES["thealleninstitute"]
            )
        finally:
            await client.aclose()
        assert len(result.records) == 3
        assert result.invalid_count == 1
        assert result.retrieved_at == FIXED_TIME
        assert result.records[0].updated_at == datetime(2026, 7, 30, 16, 0, tzinfo=UTC)

    asyncio.run(run())
    assert seen[0].method == "GET"
    assert seen[0].url.host == "boards-api.greenhouse.io"
    assert seen[0].url.path == "/v1/boards/thealleninstitute/jobs"
    assert seen[0].url.params["content"] == "true"


def test_transient_and_rate_limit_responses_use_bounded_retries() -> None:
    attempts = 0
    delays: list[float] = []

    async def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx2.Response(503)
        if attempts == 2:
            return httpx2.Response(429, headers={"Retry-After": "1"})
        return httpx2.Response(200, json={"jobs": []})

    async def record_sleep(value: float) -> None:
        delays.append(value)

    async def run() -> None:
        client, provider = build_client(
            httpx2.MockTransport(handler), sleep=record_sleep
        )
        try:
            result = await provider.fetch_board(
                OPPORTUNITY_SOURCES["thealleninstitute"]
            )
        finally:
            await client.aclose()
        assert result.records == ()

    asyncio.run(run())
    assert attempts == 3
    assert delays == [0.25, 1.0]


def test_invalid_json_is_a_safe_non_retryable_failure() -> None:
    async def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"not-json")

    async def run() -> OpportunityProviderError:
        client, provider = build_client(httpx2.MockTransport(handler))
        try:
            with pytest.raises(OpportunityProviderError) as captured:
                await provider.fetch_board(OPPORTUNITY_SOURCES["thealleninstitute"])
            return captured.value
        finally:
            await client.aclose()

    error = asyncio.run(run())
    assert error.kind is OpportunityProviderFailureKind.INVALID_RESPONSE
    assert error.retryable is False
    assert "greenhouse" not in str(error).casefold()
