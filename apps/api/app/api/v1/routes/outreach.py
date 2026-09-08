from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies.outreach import get_outreach_service
from app.dependencies.rate_limiting import rate_limit
from app.schemas.outreach import (
    OutreachDraftCreateRequest,
    OutreachDraftResponse,
    OutreachDraftUpdateRequest,
)
from app.services.outreach import OutreachReader

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post(
    "/drafts",
    response_model=OutreachDraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft from one selected researcher and selected papers",
    dependencies=[rate_limit(times=5, seconds=60)],
)
async def create_outreach_draft(
    request: OutreachDraftCreateRequest,
    service: Annotated[OutreachReader, Depends(get_outreach_service)],
) -> OutreachDraftResponse:
    return await service.create(request)


@router.get(
    "/drafts/{draft_id}",
    response_model=OutreachDraftResponse,
    summary="Read the latest owner-scoped outreach draft",
)
async def read_outreach_draft(
    draft_id: UUID,
    service: Annotated[OutreachReader, Depends(get_outreach_service)],
) -> OutreachDraftResponse:
    return await service.get(draft_id)


@router.put(
    "/drafts/{draft_id}",
    response_model=OutreachDraftResponse,
    summary="Save a new editable draft revision",
)
async def update_outreach_draft(
    draft_id: UUID,
    request: OutreachDraftUpdateRequest,
    service: Annotated[OutreachReader, Depends(get_outreach_service)],
) -> OutreachDraftResponse:
    return await service.update(draft_id, request)
