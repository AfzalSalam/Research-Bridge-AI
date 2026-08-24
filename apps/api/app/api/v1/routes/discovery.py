from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.core.rate_limit import discovery_limiter
from app.dependencies.discovery import get_paper_discovery_service
from app.schemas.discovery import PaperDiscoveryRequest, PaperDiscoveryResponse
from app.schemas.errors import ErrorResponse
from app.services.discovery import PaperDiscoveryReader

router = APIRouter(prefix="/discovery", tags=["discovery"])
error_responses: dict[int | str, dict[str, Any]] = {
    422: {
        "model": ErrorResponse,
        "description": "The paper query could not be validated or classified.",
    },
    429: {
        "model": ErrorResponse,
        "description": "Too many requests from this IP address. Please slow down.",
    },
    500: {
        "model": ErrorResponse,
        "description": "The normalized paper catalog could not be persisted.",
    },
    502: {
        "model": ErrorResponse,
        "description": "OpenAlex rejected the request or returned invalid data.",
    },
    503: {
        "model": ErrorResponse,
        "description": "OpenAlex is unreachable, rate limited, or unavailable.",
    },
}


@router.post(
    "/papers",
    response_model=PaperDiscoveryResponse,
    responses=error_responses,
    summary="Discover and persist normalized OpenAlex papers",
)
async def discover_papers(
    request: Request,
    body: PaperDiscoveryRequest,
    service: Annotated[PaperDiscoveryReader, Depends(get_paper_discovery_service)],
) -> PaperDiscoveryResponse:
    await discovery_limiter.check(request)
    return await service.search(body)
