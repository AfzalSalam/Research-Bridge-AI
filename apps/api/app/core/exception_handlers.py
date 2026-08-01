import logging
from collections.abc import Mapping, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.core.middleware import REQUEST_ID_HEADER
from app.schemas.errors import ErrorBody, ErrorDetail, ErrorResponse

logger = logging.getLogger("research_bridge.errors")


def _response(
    *,
    code: str,
    message: str,
    request_id: str,
    status_code: int,
    details: Sequence[Mapping[str, str]] | None = None,
) -> JSONResponse:
    parsed_details = [ErrorDetail.model_validate(detail) for detail in details or []]
    payload = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            details=parsed_details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers={REQUEST_ID_HEADER: request_id},
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Make domain, validation, HTTP, and unexpected failures predictable."""

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, error: AppError) -> JSONResponse:
        return _response(
            code=error.code,
            message=error.message,
            request_id=request.state.request_id,
            status_code=error.status_code,
            details=error.details,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in item["loc"] if part != "body"),
                "message": str(item["msg"]),
                "type": str(item["type"]),
            }
            for item in error.errors()
        ]
        return _response(
            code="validation_error",
            message="The request could not be validated.",
            request_id=request.state.request_id,
            status_code=422,
            details=details,
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        message = (
            error.detail if isinstance(error.detail, str) else "The request failed."
        )
        code = "not_found" if error.status_code == 404 else "http_error"
        return _response(
            code=code,
            message=message,
            request_id=request.state.request_id,
            status_code=error.status_code,
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request, error: Exception
    ) -> JSONResponse:
        logger.exception(
            "request.failed",
            exc_info=error,
            extra={"request_id": request.state.request_id},
        )
        return _response(
            code="internal_error",
            message="The server could not complete the request.",
            request_id=request.state.request_id,
            status_code=500,
        )
