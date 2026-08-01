from contextvars import ContextVar, Token

_request_id: ContextVar[str] = ContextVar("request_id", default="unavailable")


def get_request_id() -> str:
    """Return the request ID associated with the current async context."""

    return _request_id.get()


def set_request_id(request_id: str) -> Token[str]:
    """Associate a request ID and return the token needed to restore context."""

    return _request_id.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    """Restore the context that existed before request processing."""

    _request_id.reset(token)
