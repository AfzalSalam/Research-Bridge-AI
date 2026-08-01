import logging
import re
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response

from app.core.request_context import reset_request_id, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
logger = logging.getLogger("research_bridge.requests")


def resolve_request_id(candidate: str | None) -> str:
    """Continue a safe caller ID or create a new opaque request identifier."""

    if candidate and _VALID_REQUEST_ID.fullmatch(candidate):
        return candidate
    return str(uuid4())


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Attach request identity and emit metadata-only completion logs."""

    request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    token = set_request_id(request_id)
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        reset_request_id(token)
