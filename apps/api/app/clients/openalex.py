from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import quote

import httpx2
from pydantic import ValidationError

from app.providers.base import (
    AcademicProviderError,
    ClassifiedDiscoveryQuery,
    DiscoveryQueryKind,
    ProviderFailureKind,
    ProviderRateLimit,
    RawProviderSearchResult,
)
from app.providers.openalex.models import OpenAlexListEnvelope

_WORK_SELECT = ",".join(
    (
        "id",
        "doi",
        "title",
        "publication_year",
        "publication_date",
        "type",
        "language",
        "is_retracted",
        "primary_location",
        "authorships",
        "abstract_inverted_index",
        "topics",
    )
)
_TRANSIENT_STATUSES = {500, 502, 503, 504}


class OpenAlexClient:
    """Bounded OpenAlex Works adapter with secret-safe provider failures."""

    name = "OpenAlex"

    def __init__(
        self,
        client: httpx2.AsyncClient,
        *,
        api_key: str | None,
        max_attempts: int,
        backoff_base_seconds: float,
        backoff_cap_seconds: float,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_cap_seconds = backoff_cap_seconds
        self._sleep = sleep
        self._clock = clock or (lambda: datetime.now(UTC))

    async def search_papers(
        self, query: ClassifiedDiscoveryQuery, limit: int
    ) -> RawProviderSearchResult:
        params: dict[str, str | int] = {"select": _WORK_SELECT}
        if self._api_key:
            params["api_key"] = self._api_key

        exact_lookup = query.kind is not DiscoveryQueryKind.TEXT
        if query.kind is DiscoveryQueryKind.TEXT:
            path = "/works"
            params.update({"search": query.value, "per_page": limit})
        else:
            identifier = (
                query.value
                if query.kind is DiscoveryQueryKind.OPENALEX_ID
                else f"doi:{query.value}"
            )
            path = f"/works/{quote(identifier, safe='')}"

        response = await self._get(path, params=params, exact_lookup=exact_lookup)
        rate_limit = _rate_limit_from(response.headers)
        retrieved_at = self._clock()
        access_mode: Literal["api-key", "limited-anonymous"] = (
            "api-key" if self._api_key else "limited-anonymous"
        )
        if response.status_code == 404:
            return RawProviderSearchResult(
                records=(),
                total_count=0,
                retrieved_at=retrieved_at,
                rate_limit=rate_limit,
                access_mode=access_mode,
            )

        try:
            payload = response.json()
        except ValueError as error:
            raise AcademicProviderError(
                ProviderFailureKind.INVALID_RESPONSE, retryable=False
            ) from error
        if not isinstance(payload, dict):
            raise AcademicProviderError(
                ProviderFailureKind.INVALID_RESPONSE, retryable=False
            )

        if exact_lookup:
            return RawProviderSearchResult(
                records=(payload,),
                total_count=1,
                retrieved_at=retrieved_at,
                rate_limit=rate_limit,
                access_mode=access_mode,
            )

        try:
            envelope = OpenAlexListEnvelope.model_validate(payload)
        except ValidationError as error:
            raise AcademicProviderError(
                ProviderFailureKind.INVALID_RESPONSE, retryable=False
            ) from error
        return RawProviderSearchResult(
            records=tuple(envelope.results),
            total_count=envelope.meta.count,
            retrieved_at=retrieved_at,
            rate_limit=rate_limit,
            access_mode=access_mode,
        )

    async def _get(
        self,
        path: str,
        *,
        params: Mapping[str, str | int],
        exact_lookup: bool,
    ) -> httpx2.Response:
        for attempt in range(self._max_attempts):
            try:
                response = await self._client.get(path, params=params)
            except httpx2.TransportError as error:
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._backoff_delay(attempt))
                    continue
                raise AcademicProviderError(
                    ProviderFailureKind.NETWORK, retryable=True
                ) from error

            if response.status_code in _TRANSIENT_STATUSES:
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._retry_delay(response, attempt))
                    continue
                raise AcademicProviderError(
                    ProviderFailureKind.TEMPORARY,
                    retryable=True,
                    retry_after_seconds=_retry_after_seconds(response),
                )
            if response.status_code in {403, 429}:
                rate_limit = _rate_limit_from(response.headers)
                raise AcademicProviderError(
                    ProviderFailureKind.RATE_LIMIT,
                    retryable=True,
                    retry_after_seconds=(
                        _retry_after_seconds(response) or rate_limit.reset_seconds
                    ),
                )
            if response.status_code == 401:
                raise AcademicProviderError(
                    ProviderFailureKind.AUTHENTICATION, retryable=False
                )
            if response.status_code == 404 and exact_lookup:
                return response
            if response.status_code >= 400:
                raise AcademicProviderError(
                    ProviderFailureKind.REJECTED_REQUEST, retryable=False
                )
            return response

        raise AssertionError("OpenAlex retry loop exhausted without a result")

    def _backoff_delay(self, attempt: int) -> float:
        return float(
            min(
                self._backoff_base_seconds * (2**attempt),
                self._backoff_cap_seconds,
            )
        )

    def _retry_delay(self, response: httpx2.Response, attempt: int) -> float:
        retry_after = _retry_after_seconds(response)
        if retry_after is not None:
            return min(float(retry_after), self._backoff_cap_seconds)
        return self._backoff_delay(attempt)


def _optional_non_negative_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(float(value))
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _retry_after_seconds(response: httpx2.Response) -> int | None:
    return _optional_non_negative_int(response.headers.get("Retry-After"))


def _rate_limit_from(headers: Mapping[str, str]) -> ProviderRateLimit:
    return ProviderRateLimit(
        limit=_optional_non_negative_int(headers.get("X-RateLimit-Limit")),
        remaining=_optional_non_negative_int(headers.get("X-RateLimit-Remaining")),
        credits_used=_optional_non_negative_int(
            headers.get("X-RateLimit-Credits-Used")
        ),
        reset_seconds=_optional_non_negative_int(headers.get("X-RateLimit-Reset")),
    )
