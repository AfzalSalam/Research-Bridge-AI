"""Graceful rate limiter using Redis directly.

fastapi-limiter 0.2.x changed its public API entirely (now requires pyrate_limiter).
We use Redis directly with a simple sliding window counter to avoid that coupling.
"""

import logging
import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request

logger = logging.getLogger(__name__)


def rate_limit(times: int, seconds: int) -> Callable:
    """A graceful rate limiter that fails open if Redis is unavailable."""

    async def _rate_limit(request: Request) -> None:
        redis_client = getattr(request.app.state, "redis", None)
        if redis_client is None:
            # Degrade gracefully if Redis is not configured
            return

        try:
            # Use client IP as key; fall back to a fixed key if not available
            client_ip = request.client.host if request.client else "anon"
            path = request.url.path.replace("/", "_")
            key = f"rl:{client_ip}:{path}"
            window = int(time.time()) // seconds

            full_key = f"{key}:{window}"
            count = await redis_client.incr(full_key)
            if count == 1:
                await redis_client.expire(full_key, seconds * 2)

            if count > times:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {seconds} seconds.",
                )
        except HTTPException:
            raise
        except Exception:
            logger.warning("Rate limiting failed, failing open", exc_info=True)

    return Depends(_rate_limit)
