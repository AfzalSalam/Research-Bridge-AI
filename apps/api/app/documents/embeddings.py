"""Bounded embedding transport. Not yet wired to private document ingestion."""

import asyncio
import math
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx2
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, ValidationError

from app.core.config import Settings

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MAX_BATCH = 32
MAX_INPUT_CHARACTERS = 1200
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class EmbeddingError(Exception):
    def __init__(self, code: str, *, retry_after: int = 0) -> None:
        super().__init__(code)
        self.code, self.retry_after = code, retry_after


class _Vector(BaseModel):
    model_config = ConfigDict(strict=True)
    index: int = Field(ge=0, lt=MAX_BATCH)
    embedding: list[FiniteFloat] = Field(
        min_length=EMBEDDING_DIMENSIONS, max_length=EMBEDDING_DIMENSIONS
    )


class _Usage(BaseModel):
    model_config = ConfigDict(strict=True)
    prompt_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class _Response(BaseModel):
    model_config = ConfigDict(strict=True)
    model: str
    data: list[_Vector] = Field(min_length=1, max_length=MAX_BATCH)
    usage: _Usage


@dataclass(frozen=True)
class EmbeddingBatch:
    model: str
    dimensions: int
    vectors: tuple[tuple[float, ...], ...]
    prompt_tokens: int


def retry_delay(value: str | None) -> int:
    if not value:
        return 1
    try:
        delay = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=UTC)
            delay = (date - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return 1
    if not math.isfinite(delay):
        return 1
    return max(1, min(3600, math.ceil(delay)))


class OpenAIEmbeddings:
    path = "embeddings"

    def payload(self, inputs: list[str]) -> dict[str, object]:
        return {
            "model": EMBEDDING_MODEL,
            "dimensions": EMBEDDING_DIMENSIONS,
            "encoding_format": "float",
            "input": inputs,
        }

    def validate(self, body: bytes, count: int) -> EmbeddingBatch:
        return validate_response(body, count)

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not settings.openai_api_key:
            raise EmbeddingError("embeddings_not_configured")
        self._sleep = sleep
        self._client = httpx2.AsyncClient(
            base_url=settings.openai_base_url + "/",
            headers={
                "Authorization": "Bearer " + settings.openai_api_key.get_secret_value(),
                "Accept-Encoding": "identity",
            },
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx2.Timeout(20, connect=5, pool=5),
            limits=httpx2.Limits(max_connections=2, max_keepalive_connections=2),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def embed(self, inputs: Sequence[str]) -> EmbeddingBatch:
        # A Unicode character is at most four UTF-8 bytes: this conservative
        # bound stays below the provider's per-input and per-request token caps.
        if (
            isinstance(inputs, str)
            or not 1 <= len(inputs) <= MAX_BATCH
            or any(
                not item.strip() or len(item) > MAX_INPUT_CHARACTERS for item in inputs
            )
        ):
            raise EmbeddingError("invalid_embedding_input")
        try:
            async with asyncio.timeout(65):
                return await self._embed(list(inputs))
        except TimeoutError:
            raise EmbeddingError("embedding_timeout", retry_after=30) from None

    async def _embed(self, inputs: list[str]) -> EmbeddingBatch:
        for attempt in range(3):
            try:
                async with self._client.stream(
                    "POST",
                    self.path,
                    json=self.payload(inputs),
                ) as response:
                    if response.status_code in {429, 500, 502, 503, 504}:
                        delay = retry_delay(response.headers.get("retry-after"))
                        if attempt == 2 or delay > 5:
                            raise EmbeddingError(
                                "embedding_provider_unavailable", retry_after=delay
                            )
                    elif response.status_code != 200:
                        raise EmbeddingError("embedding_provider_refused")
                    else:
                        if (
                            response.headers.get("content-encoding", "identity")
                            != "identity"
                        ):
                            raise EmbeddingError("invalid_embedding_response")
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                                raise EmbeddingError("embedding_response_too_large")
                            body.extend(chunk)
                        return self.validate(bytes(body), len(inputs))
            except httpx2.TransportError:
                if attempt == 2:
                    raise EmbeddingError(
                        "embedding_provider_unavailable", retry_after=30
                    ) from None
                delay = 2**attempt
            await self._sleep(delay)
        raise AssertionError("Embedding retry loop exhausted")


def validate_response(body: bytes, count: int) -> EmbeddingBatch:
    try:
        result = _Response.model_validate_json(body)
    except ValidationError:
        raise EmbeddingError("invalid_embedding_response") from None
    if (
        result.model != EMBEDDING_MODEL
        or len(result.data) != count
        or {item.index for item in result.data} != set(range(count))
        or result.usage.total_tokens < result.usage.prompt_tokens
    ):
        raise EmbeddingError("invalid_embedding_response")
    vectors: list[tuple[float, ...]] = []
    for item in sorted(result.data, key=lambda item: item.index):
        norm = math.hypot(*item.embedding)
        if not math.isfinite(norm) or norm == 0:
            raise EmbeddingError("invalid_embedding_response")
        vectors.append(tuple(value / norm for value in item.embedding))
    return EmbeddingBatch(
        EMBEDDING_MODEL,
        EMBEDDING_DIMENSIONS,
        tuple(vectors),
        result.usage.prompt_tokens,
    )
