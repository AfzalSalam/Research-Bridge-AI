from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.routes.discovery import error_responses
from app.dependencies.mentor_discovery import get_mentor_discovery_service
from app.schemas.errors import ErrorResponse
from app.schemas.mentor_discovery import (
    MentorDiscoveryRequest,
    MentorDiscoveryResponse,
)
from app.services.mentor_discovery import MentorDiscoveryReader

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post(
    "/mentors",
    response_model=MentorDiscoveryResponse,
    responses={
        **error_responses,
        401: {"model": ErrorResponse, "description": "Sign in to discover mentors."},
        409: {
            "model": ErrorResponse,
            "description": "Save your student profile first.",
        },
    },
    summary="Derive explainable professor candidates from paper evidence",
)
async def discover_mentors(
    body: MentorDiscoveryRequest,
    service: Annotated[MentorDiscoveryReader, Depends(get_mentor_discovery_service)],
) -> MentorDiscoveryResponse:
    return await service.search(body)
