from pydantic import Field

from app.schemas.base import ApiModel


class ErrorDetail(ApiModel):
    """One safe, machine-readable explanation of an invalid input field."""

    field: str
    message: str
    type: str


class ErrorBody(ApiModel):
    """Stable error information returned by every API failure."""

    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(ApiModel):
    """Top-level error envelope shared across routes and status codes."""

    error: ErrorBody
