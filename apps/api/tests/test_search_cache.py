import asyncio
from datetime import UTC, datetime

from app.providers.base import (
    DiscoveryQueryKind,
    NormalizedProviderSearchResult,
    ProviderRateLimit,
)
from app.services.search_cache import MemoryPaperSearchCache, SearchCacheKey


def empty_result() -> NormalizedProviderSearchResult:
    return NormalizedProviderSearchResult(
        papers=(),
        total_count=0,
        skipped_count=0,
        invalid_count=0,
        excluded_count=0,
        warnings=(),
        retrieved_at=datetime(2026, 8, 1, tzinfo=UTC),
        rate_limit=ProviderRateLimit(),
        access_mode="limited-anonymous",
    )


def key(value: str) -> SearchCacheKey:
    return SearchCacheKey(
        provider="OpenAlex",
        query_kind=DiscoveryQueryKind.TEXT,
        query_value=value,
        limit=12,
    )


def test_memory_cache_expires_entries() -> None:
    now = 10.0
    cache = MemoryPaperSearchCache(ttl_seconds=30, max_entries=2, clock=lambda: now)

    async def run() -> None:
        nonlocal now
        await cache.set(key("one"), empty_result())
        assert await cache.get(key("one")) is not None
        now = 40.0
        assert await cache.get(key("one")) is None

    asyncio.run(run())


def test_memory_cache_evicts_the_least_recently_used_entry() -> None:
    cache = MemoryPaperSearchCache(ttl_seconds=30, max_entries=2, clock=lambda: 10.0)

    async def run() -> None:
        await cache.set(key("one"), empty_result())
        await cache.set(key("two"), empty_result())
        assert await cache.get(key("one")) is not None
        await cache.set(key("three"), empty_result())
        assert await cache.get(key("one")) is not None
        assert await cache.get(key("two")) is None
        assert await cache.get(key("three")) is not None

    asyncio.run(run())
