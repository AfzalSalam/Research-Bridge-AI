"""In-process sliding-window IP rate limiter for costly API routes.

This is a placement-release guard only. It cannot coordinate across multiple
API replicas. Redis-backed distributed limiting remains deferred until measured
load warrants it.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque

from fastapi import Request

from app.core.errors import AppError


class _SlidingWindowCounter:
    """Thread-safe sliding window request counter for a single IP address."""

    __slots__ = ("_lock", "_timestamps", "_window_seconds")

    def __init__(self, window_seconds: float) -> None:
        self._window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def record_and_check(self, limit: int) -> int:
        """Record a request and return the current count within the window."""

        now = time.monotonic()
        cutoff = now - self._window_seconds
        async with self._lock:
            # Evict expired entries
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()
            self._timestamps.append(now)
            return len(self._timestamps)


class InProcessRateLimiter:
    """Per-IP sliding-window rate limiter stored in process memory.

    Routes that call ``check`` will raise ``AppError(429)`` when the caller
    exceeds ``limit`` requests within ``window_seconds``.
    """

    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._counters: dict[str, _SlidingWindowCounter] = {}
        self._global_lock = asyncio.Lock()

    async def _get_counter(self, ip: str) -> _SlidingWindowCounter:
        async with self._global_lock:
            if ip not in self._counters:
                self._counters[ip] = _SlidingWindowCounter(self._window_seconds)
            return self._counters[ip]

    async def check(self, request: Request) -> None:
        """Raise 429 if the client IP has exceeded the configured rate limit."""

        ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )
        counter = await self._get_counter(ip)
        count = await counter.record_and_check(self._limit)
        if count > self._limit:
            raise AppError(
                code="rate_limit_exceeded",
                message=(
                    "Too many requests. Please wait before trying again."
                ),
                status_code=429,
            )


# Shared limiter for expensive discovery and outreach routes.
# 30 requests per 60-second window per IP address.
discovery_limiter = InProcessRateLimiter(limit=30, window_seconds=60.0)
