from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.dependencies.services import get_demo_service
from app.schemas.demo import (
    DemoBootstrapResponse,
    DiscoveryRequest,
    DiscoveryResponse,
    OutreachDraft,
    OutreachDraftRequest,
)
from app.schemas.errors import ErrorResponse
from app.services.demo import DemoService

router = APIRouter(prefix="/demo", tags=["demo"])
error_responses: dict[int | str, dict[str, Any]] = {
    404: {
        "model": ErrorResponse,
        "description": "Requested demo evidence was not found.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Request or evidence selection is invalid.",
    },
    500: {
        "model": ErrorResponse,
        "description": "The server could not complete the request.",
    },
    503: {
        "model": ErrorResponse,
        "description": "The selected fictional source failed.",
    },
}


@router.get(
    "/bootstrap",
    response_model=DemoBootstrapResponse,
    responses={500: error_responses[500]},
    summary="Load the fictional demo catalog",
)
async def read_demo_bootstrap(
    service: Annotated[DemoService, Depends(get_demo_service)],
) -> DemoBootstrapResponse:
    return await service.bootstrap()


@router.post(
    "/discovery",
    response_model=DiscoveryResponse,
    responses=error_responses,
    summary="Run a deterministic discovery scenario",
)
async def run_demo_discovery(
    request: DiscoveryRequest,
    service: Annotated[DemoService, Depends(get_demo_service)],
) -> DiscoveryResponse:
    return await service.discover(request)


@router.post(
    "/outreach-drafts",
    response_model=OutreachDraft,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses,
    summary="Create an editable evidence-grounded demo draft",
)
async def create_demo_outreach_draft(
    request: OutreachDraftRequest,
    service: Annotated[DemoService, Depends(get_demo_service)],
) -> OutreachDraft:
    return await service.create_outreach_draft(request)
