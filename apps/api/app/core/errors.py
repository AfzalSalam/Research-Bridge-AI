from collections.abc import Mapping


class AppError(Exception):
    """An expected domain or dependency failure safe to expose to clients."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: list[Mapping[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
