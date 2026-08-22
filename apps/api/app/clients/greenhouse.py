from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx2
from pydantic import ValidationError

from app.providers.greenhouse.models import GreenhouseEnvelope, GreenhouseJob
from app.providers.opportunities import (
    OpportunityProviderError,
    OpportunityProviderFailureKind,
    OpportunitySource,
    RawOpportunityBoard,
    RawOpportunityRecord,
)

_TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
_MAX_RESPONSE_BYTES = 5_000_000


class GreenhouseClient:
    """Fixed-origin reader for allowlisted public Greenhouse job boards."""

    def __init__(
        self,
        client: httpx2.AsyncClient,
        *,
        max_attempts: int,
        backoff_base_seconds: float,
        backoff_cap_seconds: float,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_cap_seconds = backoff_cap_seconds
        self._sleep = sleep
        self._clock = clock or (lambda: datetime.now(UTC))

    async def fetch_board(self, source: OpportunitySource) -> RawOpportunityBoard:
        response = await self._get(
            f"/v1/boards/{source.key}/jobs", params={"content": "true"}
        )
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise OpportunityProviderError(
                OpportunityProviderFailureKind.INVALID_RESPONSE, retryable=False
            )
        try:
            payload = response.json()
            envelope = GreenhouseEnvelope.model_validate(payload)
        except (ValueError, ValidationError) as error:
            raise OpportunityProviderError(
                OpportunityProviderFailureKind.INVALID_RESPONSE, retryable=False
            ) from error

        records: list[RawOpportunityRecord] = []
        invalid_count = 0
        for raw_job in envelope.jobs:
            try:
                job = GreenhouseJob.model_validate(raw_job)
            except ValidationError:
                invalid_count += 1
                continue
            records.append(
                RawOpportunityRecord(
                    id=job.id,
                    title=job.title,
                    updated_at=_as_utc(job.updated_at),
                    location=job.location.name,
                    absolute_url=str(job.absolute_url),
                    content=job.content,
                    departments=tuple(item.name for item in job.departments),
                )
            )
        if envelope.jobs and not records:
            raise OpportunityProviderError(
                OpportunityProviderFailureKind.INVALID_RESPONSE, retryable=False
            )
        return RawOpportunityBoard(
            source=source,
            records=tuple(records),
            invalid_count=invalid_count,
            retrieved_at=_as_utc(self._clock()),
        )

    async def _get(self, path: str, *, params: dict[str, str]) -> httpx2.Response:
        for attempt in range(self._max_attempts):
            try:
                response = await self._client.get(path, params=params)
            except httpx2.TransportError as error:
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._backoff_delay(attempt))
                    continue
                raise OpportunityProviderError(
                    OpportunityProviderFailureKind.NETWORK, retryable=True
                ) from error

            if response.status_code in _TRANSIENT_STATUSES:
                retry_after = _retry_after_seconds(response)
                if attempt + 1 < self._max_attempts:
                    await self._sleep(
                        min(
                            float(retry_after)
                            if retry_after is not None
                            else self._backoff_delay(attempt),
                            self._backoff_cap_seconds,
                        )
                    )
                    continue
                kind = (
                    OpportunityProviderFailureKind.RATE_LIMIT
                    if response.status_code == 429
                    else OpportunityProviderFailureKind.TEMPORARY
                )
                raise OpportunityProviderError(
                    kind,
                    retryable=True,
                    retry_after_seconds=retry_after,
                )
            if response.status_code >= 400:
                raise OpportunityProviderError(
                    OpportunityProviderFailureKind.REJECTED_REQUEST,
                    retryable=False,
                )
            return response
        raise AssertionError("Greenhouse retry loop exhausted without a result")

    def _backoff_delay(self, attempt: int) -> float:
        return float(
            min(
                self._backoff_base_seconds * (2**attempt),
                self._backoff_cap_seconds,
            )
        )


def _retry_after_seconds(response: httpx2.Response) -> int | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        parsed = int(float(value))
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _as_utc(value: datetime) -> datetime:
    """Normalize provider and injected-clock values to the public UTC contract."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
