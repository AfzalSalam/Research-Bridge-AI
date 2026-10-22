"""Bounded Gemini answer transport; not enabled in application routes."""

import asyncio
import json
from typing import Literal

import httpx2
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.documents.answers import (
    AnswerProviderError,
    SupportReview,
    checked_json,
)
from app.documents.citation_choices import (
    CHOICE_SYSTEM,
    Selection,
    catalog,
    materialize,
)

ANSWER_MODEL = "gemini-3.1-flash-lite"
MAX_REQUEST_BYTES = 128_000
MAX_ENVELOPE_BYTES = 128_000


class _Part(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    text: str
    thought: Literal[False] = False
    thoughtSignature: str | None = Field(default=None, max_length=16000, exclude=True)


class _Content(BaseModel):
    model_config = ConfigDict(strict=True)
    role: Literal["model"]
    parts: list[_Part] = Field(min_length=1, max_length=4)


class _Candidate(BaseModel):
    model_config = ConfigDict(strict=True)
    content: _Content
    finishReason: Literal["STOP"]


class _Envelope(BaseModel):
    model_config = ConfigDict(strict=True)
    candidates: list[_Candidate] = Field(min_length=1, max_length=1)
    modelVersion: str


class GeminiAnswerProvider:
    def __init__(
        self, settings: Settings, *, transport: httpx2.AsyncBaseTransport | None = None
    ) -> None:
        if not settings.gemini_api_key:
            raise AnswerProviderError("answer_provider_not_configured")
        self._client = httpx2.AsyncClient(
            base_url="https://generativelanguage.googleapis.com/v1beta/",
            headers={
                "x-goog-api-key": settings.gemini_api_key.get_secret_value(),
                "Accept-Encoding": "identity",
                "Content-Type": "application/json",
            },
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx2.Timeout(25, connect=5, pool=5),
            limits=httpx2.Limits(max_connections=1, max_keepalive_connections=1),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate(self, system: str, payload: str) -> str:
        try:
            enriched, choices = catalog(payload)
            raw = await self._request(CHOICE_SYSTEM, enriched, Selection, 2048)
            return materialize(raw, choices)
        except (ValueError, KeyError, TypeError):
            raise AnswerProviderError("invalid_answer_choices") from None

    async def review(self, system: str, payload: str) -> str:
        return await self._request(system, payload, SupportReview, 1024)

    async def _request(
        self, system: str, payload: str, schema: type[BaseModel], tokens: int
    ) -> str:
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": payload}]}],
                "generationConfig": {
                    "candidateCount": 1,
                    "temperature": 0,
                    "maxOutputTokens": tokens,
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema.model_json_schema(),
                    "thinkingConfig": {"thinkingLevel": "minimal"},
                },
            }
        ).encode()
        if len(body) > MAX_REQUEST_BYTES:
            raise AnswerProviderError("answer_input_too_large")
        try:
            async with asyncio.timeout(28):
                async with self._client.stream(
                    "POST", f"models/{ANSWER_MODEL}:generateContent", content=body
                ) as response:
                    if response.status_code != 200:
                        # Do not blindly retry ambiguous/cost-incurring outcomes.
                        raise AnswerProviderError("answer_provider_refused")
                    if (
                        response.headers.get("content-encoding", "identity")
                        != "identity"
                    ):
                        raise AnswerProviderError("invalid_answer_envelope")
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(raw) + len(chunk) > MAX_ENVELOPE_BYTES:
                            raise AnswerProviderError("answer_response_too_large")
                        raw.extend(chunk)
            envelope = _Envelope.model_validate_json(bytes(raw))
            if (
                envelope.modelVersion != ANSWER_MODEL
                and not envelope.modelVersion.startswith(ANSWER_MODEL + "-")
            ):
                raise AnswerProviderError("unexpected_answer_model")
            result = checked_json(
                "".join(p.text for p in envelope.candidates[0].content.parts)
            )
            schema.model_validate_json(result)
            return result
        except (httpx2.TransportError, TimeoutError):
            raise AnswerProviderError("answer_provider_unavailable") from None
        except (ValidationError, ValueError):
            raise AnswerProviderError("invalid_answer_envelope") from None
