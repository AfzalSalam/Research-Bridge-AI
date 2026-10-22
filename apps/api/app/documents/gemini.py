"""Single-input Gemini REST adapter; shares bounded transport/retries with OpenAI."""

import asyncio
import math
from collections.abc import Awaitable, Callable

import httpx2
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, ValidationError

from app.core.config import Settings
from app.documents.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingBatch,
    EmbeddingError,
    OpenAIEmbeddings,
)

GEMINI_MODEL = "gemini-embedding-2"


class _Embedding(BaseModel):
    model_config = ConfigDict(strict=True)
    values: list[FiniteFloat] = Field(
        min_length=EMBEDDING_DIMENSIONS, max_length=EMBEDDING_DIMENSIONS
    )


class _Response(BaseModel):
    model_config = ConfigDict(strict=True)
    embedding: _Embedding


class GeminiEmbeddings(OpenAIEmbeddings):
    path = "models/gemini-embedding-2:embedContent"

    def __init__(
        self,
        settings: Settings,
        *,
        query: bool = False,
        transport: httpx2.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not settings.gemini_api_key:
            raise EmbeddingError("embeddings_not_configured")
        self._query, self._sleep = query, sleep
        self._client = httpx2.AsyncClient(
            base_url="https://generativelanguage.googleapis.com/v1beta/",
            headers={
                "x-goog-api-key": settings.gemini_api_key.get_secret_value(),
                "Accept-Encoding": "identity",
            },
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx2.Timeout(20, connect=5, pool=5),
            limits=httpx2.Limits(max_connections=1, max_keepalive_connections=1),
        )

    def payload(self, inputs: list[str]) -> dict[str, object]:
        # Embedding 2 aggregates multiple content parts: never merge paper chunks.
        if len(inputs) != 1:
            raise EmbeddingError("invalid_embedding_input")
        prefix = (
            "task: search result | query: " if self._query else "title: none | text: "
        )
        return {
            "model": "models/" + GEMINI_MODEL,
            "content": {"parts": [{"text": prefix + inputs[0]}]},
            "outputDimensionality": EMBEDDING_DIMENSIONS,
        }

    def validate(self, body: bytes, count: int) -> EmbeddingBatch:
        try:
            response = _Response.model_validate_json(body)
        except ValidationError:
            raise EmbeddingError("invalid_embedding_response") from None
        norm = math.hypot(*response.embedding.values)
        if count != 1 or norm == 0 or not math.isfinite(norm):
            raise EmbeddingError("invalid_embedding_response")
        vector = tuple(value / norm for value in response.embedding.values)
        # This endpoint does not report token usage; quota uses reserved UTF-8 bytes.
        return EmbeddingBatch(GEMINI_MODEL, EMBEDDING_DIMENSIONS, (vector,), 0)
