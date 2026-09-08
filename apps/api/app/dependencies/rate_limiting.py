import logging
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
            from fastapi_limiter.depends import RateLimiter
            limiter = RateLimiter(times=times, seconds=seconds)
            await limiter(request=request)
        except HTTPException:
            raise
        except Exception:
            logger.warning("Rate limiting failed, failing open", exc_info=True)

    return Depends(_rate_limit)
