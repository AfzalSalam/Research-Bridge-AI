from typing import cast

from fastapi import APIRouter, Request

from app.core.config import Settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def read_health(request: Request) -> HealthResponse:
    """Report that the API process and typed contract are available."""

    settings = cast(Settings, request.app.state.settings)
    return HealthResponse(
        service="research-bridge-api",
        version=settings.app_version,
        environment=settings.app_environment,
    )
