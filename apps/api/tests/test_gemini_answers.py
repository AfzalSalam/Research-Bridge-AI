"""Transport fixtures do not measure answer accuracy."""

import asyncio
import json
from functools import wraps

import httpx2
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.documents.answers import AnswerProviderError, Candidate
from app.documents.gemini_answers import ANSWER_MODEL, GeminiAnswerProvider


def run_async(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapped


RESULT = {"status": "insufficient_evidence", "claims": []}


def envelope(result=RESULT):
    return {
        "modelVersion": ANSWER_MODEL,
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [
                        {"text": json.dumps(result), "thoughtSignature": "opaque"}
                    ],
                },
                "finishReason": "STOP",
            }
        ],
    }


def provider(handler):
    return GeminiAnswerProvider(
        Settings(_env_file=None, gemini_api_key=SecretStr("fixture-secret")),
        transport=httpx2.MockTransport(handler),
    )


@run_async
async def test_request_contract():
    requests = []

    def handler(request):
        requests.append(request)
        body = json.loads(request.content)
        assert request.url.host == "generativelanguage.googleapis.com"
        assert "fixture-secret" not in str(request.url)
        assert request.headers["x-goog-api-key"] == "fixture-secret"
        assert body["systemInstruction"]["parts"][0]["text"] == "rules"
        assert body["contents"][0]["parts"][0]["text"] == "untrusted"
        assert "tools" not in body
        assert body["generationConfig"]["maxOutputTokens"] in (2048, 1024)
        assert body["generationConfig"]["responseJsonSchema"]
        result = (
            RESULT
            if len(requests) == 1
            else {
                "addresses_question": True,
                "claims": [{"index": 0, "verdict": "supported"}],
            }
        )
        return httpx2.Response(200, json=envelope(result))

    client = provider(handler)
    try:
        assert (
            json.loads(await client._request("rules", "untrusted", Candidate, 2048))
            == RESULT
        )
        await client.review("rules", "untrusted")
        assert len(requests) == 2
    finally:
        await client.aclose()


@run_async
@pytest.mark.parametrize(
    "case",
    ["truncated", "empty", "multiple", "model", "tool", "json", "large", "encoding"],
)
async def test_rejects_invalid_envelopes(case):
    payload = envelope()
    headers = {}
    if case == "truncated":
        payload["candidates"][0]["finishReason"] = "MAX_TOKENS"
    elif case == "empty":
        payload["candidates"] = []
    elif case == "multiple":
        payload["candidates"] *= 2
    elif case == "model":
        payload["modelVersion"] = "unexpected"
    elif case == "tool":
        payload["candidates"][0]["content"]["parts"] = [{"functionCall": {}}]
    elif case == "json":
        payload["candidates"][0]["content"]["parts"][0]["text"] = (
            "private-invalid-output"
        )
    elif case == "large":
        payload["padding"] = "x" * 128001
    elif case == "encoding":
        headers["content-encoding"] = "unsupported"
    client = provider(
        lambda request: httpx2.Response(200, json=payload, headers=headers)
    )
    try:
        with pytest.raises(AnswerProviderError) as caught:
            await client._request("rules", "question", Candidate, 2048)
        assert "private-invalid-output" not in str(caught.value)
    finally:
        await client.aclose()


@run_async
@pytest.mark.parametrize("status", [302, 429, 500])
async def test_provider_failures_never_retry(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(
            status,
            text="private provider details",
            headers={"Location": "https://example.com"},
        )

    client = provider(handler)
    try:
        with pytest.raises(AnswerProviderError, match="^answer_provider_refused$"):
            await client._request("rules", "question", Candidate, 2048)
        assert len(calls) == 1
    finally:
        await client.aclose()


@run_async
async def test_input_limit_before_network():
    def handler(request):
        pytest.fail("oversized input reached network")

    client = provider(handler)
    try:
        with pytest.raises(AnswerProviderError, match="answer_input_too_large"):
            await client._request("rules", "x" * 128001, Candidate, 2048)
    finally:
        await client.aclose()


@run_async
@pytest.mark.parametrize("cancel", [False, True])
async def test_timeout_redaction_and_cancellation(cancel):
    def handler(request):
        if cancel:
            raise asyncio.CancelledError()
        raise httpx2.ReadTimeout("private timeout details")

    client = provider(handler)
    try:
        expected = asyncio.CancelledError if cancel else AnswerProviderError
        with pytest.raises(expected) as caught:
            await client._request("rules", "question", Candidate, 2048)
        assert "private timeout details" not in str(caught.value)
    finally:
        await client.aclose()
