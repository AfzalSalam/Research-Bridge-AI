from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from app.providers.base import DiscoveryQueryKind, NormalizedProviderSearchResult

NORMALIZER_VERSION = "openalex-v1"


@dataclass(frozen=True, slots=True)
class SearchCacheKey:
    provider: str
    query_kind: DiscoveryQueryKind
    query_value: str
    limit: int
    normalizer_version: str = NORMALIZER_VERSION


class PaperSearchCache(Protocol):
    async def get(
        self, key: SearchCacheKey
    ) -> NormalizedProviderSearchResult | None: ...

    async def set(
        self, key: SearchCacheKey, value: NormalizedProviderSearchResult
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    value: NormalizedProviderSearchResult
    expires_at: float


class MemoryPaperSearchCache:
    """Small process-local TTL/LRU cache; values never contain ORM state."""

    def __init__(
        self,
        *,
        ttl_seconds: int,
        max_entries: int,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[SearchCacheKey, _CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: SearchCacheKey) -> NormalizedProviderSearchResult | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry.value

    async def set(
        self, key: SearchCacheKey, value: NormalizedProviderSearchResult
    ) -> None:
        async with self._lock:
            self._entries[key] = _CacheEntry(
                value=value, expires_at=self._clock() + self._ttl_seconds
            )
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
