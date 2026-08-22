from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.opportunities import get_application_tracker_service
from app.schemas.opportunities import (
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdateRequest,
)
from app.services.applications import ApplicationTrackerReader

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track one explicitly saved opportunity",
)
async def create_application(
    request: ApplicationCreateRequest,
    service: Annotated[
        ApplicationTrackerReader, Depends(get_application_tracker_service)
    ],
) -> ApplicationResponse:
    return await service.create(request)


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="List owner-scoped application records and history",
)
async def list_applications(
    service: Annotated[
        ApplicationTrackerReader, Depends(get_application_tracker_service)
    ],
) -> ApplicationListResponse:
    return await service.list()


@router.put(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update explicit tracker state with optimistic versioning",
)
async def update_application(
    application_id: UUID,
    request: ApplicationUpdateRequest,
    service: Annotated[
        ApplicationTrackerReader, Depends(get_application_tracker_service)
    ],
) -> ApplicationResponse:
    return await service.update(application_id, request)
