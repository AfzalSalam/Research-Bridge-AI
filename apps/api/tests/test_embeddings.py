import asyncio
import json
from unittest.mock import AsyncMock

import httpx2
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.documents.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    MAX_RESPONSE_BYTES,
    EmbeddingError,
    OpenAIEmbeddings,
    retry_delay,
    validate_response,
)


def payload(count=1):
    return {
        "model": EMBEDDING_MODEL,
        "data": [
            {
                "index": i,
                "embedding": [float(i + 1)] + [0.0] * (EMBEDDING_DIMENSIONS - 1),
            }
            for i in range(count)
        ],
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }


def settings():
    return Settings(_env_file=None, openai_api_key=SecretStr("fixture-secret"))


def test_order_normalization_and_bounded_request():
    async def run():
        def handler(request):
            assert str(request.url) == "https://api.openai.com/v1/embeddings"
            assert request.headers["authorization"] == "Bearer fixture-secret"
            sent = json.loads(request.content)
            assert sent == {
                "model": EMBEDDING_MODEL,
                "dimensions": EMBEDDING_DIMENSIONS,
                "encoding_format": "float",
                "input": ["one", "two"],
            }
            response = payload(2)
            response["data"][1]["embedding"][0] = 0.0
            response["data"][1]["embedding"][1] = 2.0
            response["data"].reverse()
            return httpx2.Response(200, json=response)

        client = OpenAIEmbeddings(settings(), transport=httpx2.MockTransport(handler))
        try:
            result = await client.embed(["one", "two"])
            assert result.model == EMBEDDING_MODEL
            assert result.dimensions == EMBEDDING_DIMENSIONS
            assert len(result.vectors) == 2
            assert result.vectors[0][0] == 1.0
            assert result.vectors[1][1] == 1.0
            assert result.prompt_tokens == 5
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("inputs", [[], [" "], ["x" * 1201], ["x"] * 33, "text"])
def test_invalid_inputs_never_call_provider(inputs):
    async def run():
        handler = AsyncMock()
        client = OpenAIEmbeddings(settings(), transport=httpx2.MockTransport(handler))
        try:
            with pytest.raises(EmbeddingError, match="invalid_embedding_input"):
                await client.embed(inputs)
            handler.assert_not_called()
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "case",
    [
        "model",
        "missing",
        "duplicate",
        "dimension",
        "nan",
        "infinity",
        "zero",
        "string",
        "bool",
        "usage",
    ],
)
def test_malformed_vectors_are_rejected(case):
    value = payload(2)
    if case == "model":
        value["model"] = "different-model"
    if case == "missing":
        value["data"].pop()
    if case == "duplicate":
        value["data"][1]["index"] = 0
    if case == "dimension":
        value["data"][0]["embedding"].pop()
    if case == "nan":
        value["data"][0]["embedding"][0] = float("nan")
    if case == "infinity":
        value["data"][0]["embedding"][0] = float("inf")
    if case == "zero":
        value["data"][0]["embedding"][0] = 0
    if case == "string":
        value["data"][0]["embedding"][0] = "1.0"
    if case == "bool":
        value["data"][0]["index"] = True
    if case == "usage":
        value["usage"]["total_tokens"] = 0
    with pytest.raises(EmbeddingError, match="invalid_embedding_response"):
        validate_response(json.dumps(value).encode(), 2)


@pytest.mark.parametrize(
    "status,expected_calls", [(429, 3), (503, 3), (401, 1), (302, 1)]
)
def test_bounded_retries_and_safe_errors(status, expected_calls):
    async def run():
        handler = AsyncMock(
            return_value=httpx2.Response(status, text="private echoed text")
        )
        sleep = AsyncMock()
        client = OpenAIEmbeddings(
            settings(), transport=httpx2.MockTransport(handler), sleep=sleep
        )
        try:
            with pytest.raises(EmbeddingError) as error:
                await client.embed(["private paper text"])
            assert "private" not in str(error.value)
            assert handler.call_count == expected_calls
            assert sleep.call_count == expected_calls - 1
        finally:
            await client.aclose()

    asyncio.run(run())


def test_retry_after_is_deferred_instead_of_retrying_early():
    async def run():
        handler = AsyncMock(
            return_value=httpx2.Response(429, headers={"Retry-After": "120"})
        )
        sleep = AsyncMock()
        client = OpenAIEmbeddings(
            settings(), transport=httpx2.MockTransport(handler), sleep=sleep
        )
        try:
            with pytest.raises(EmbeddingError) as error:
                await client.embed(["fixture"])
            assert error.value.retry_after == 120
            assert handler.call_count == 1
            sleep.assert_not_called()
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "body",
    [b"not-json", b"x" * (MAX_RESPONSE_BYTES + 1)],
    ids=["invalid-json", "oversized"],
)
def test_response_limit_and_invalid_json(body):
    async def run():
        handler = AsyncMock(return_value=httpx2.Response(200, content=body))
        client = OpenAIEmbeddings(settings(), transport=httpx2.MockTransport(handler))
        try:
            with pytest.raises(EmbeddingError):
                await client.embed(["fixture"])
            assert handler.call_count == 1
        finally:
            await client.aclose()

    asyncio.run(run())


def test_transient_failure_recovers():
    async def run():
        handler = AsyncMock(
            side_effect=[
                httpx2.ConnectError("fixture"),
                httpx2.Response(200, json=payload()),
            ]
        )
        sleep = AsyncMock()
        client = OpenAIEmbeddings(
            settings(), transport=httpx2.MockTransport(handler), sleep=sleep
        )
        try:
            assert len((await client.embed(["fixture"])).vectors) == 1
            assert handler.call_count == 2
            sleep.assert_awaited_once()
        finally:
            await client.aclose()

    asyncio.run(run())


def test_no_credentials_and_untrusted_retry_header():
    with pytest.raises(EmbeddingError, match="embeddings_not_configured"):
        OpenAIEmbeddings(Settings(_env_file=None, openai_api_key=None))
    assert retry_delay("nan") == 1
    assert retry_delay("garbage") == 1
    assert retry_delay("9999999") == 3600
    assert retry_delay("Thu, 01 Jan 1970 00:00:00 GMT") == 1


def test_cancelled_request_is_not_retried():
    async def run():
        entered = asyncio.Event()

        async def handler(request):
            entered.set()
            await asyncio.Event().wait()

        sleep = AsyncMock()
        client = OpenAIEmbeddings(
            settings(), transport=httpx2.MockTransport(handler), sleep=sleep
        )
        try:
            task = asyncio.create_task(client.embed(["fixture"]))
            await asyncio.wait_for(entered.wait(), timeout=2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            sleep.assert_not_called()
        finally:
            await client.aclose()

    asyncio.run(run())


def test_transport_timeout_is_bounded():
    async def run():
        handler = AsyncMock(side_effect=httpx2.ReadTimeout("fixture"))
        sleep = AsyncMock()
        client = OpenAIEmbeddings(
            settings(), transport=httpx2.MockTransport(handler), sleep=sleep
        )
        try:
            with pytest.raises(EmbeddingError) as error:
                await client.embed(["fixture"])
            assert error.value.code == "embedding_provider_unavailable"
            assert handler.call_count == 3
        finally:
            await client.aclose()

    asyncio.run(run())
