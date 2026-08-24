from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.dependencies.opportunities import (
    get_opportunity_search_service,
    get_opportunity_service,
)
from app.schemas.opportunities import (
    OpportunitySearchRequest,
    OpportunitySearchResponse,
    SavedOpportunity,
    SavedOpportunityListResponse,
)
from app.services.opportunities import OpportunityReader

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.post(
    "/search",
    response_model=OpportunitySearchResponse,
    summary="Search allowlisted employer-published research opportunities",
)
async def search_opportunities(
    request: OpportunitySearchRequest,
    service: Annotated[OpportunityReader, Depends(get_opportunity_search_service)],
) -> OpportunitySearchResponse:
    return await service.search(request)


@router.post(
    "/{opportunity_id}/save",
    response_model=SavedOpportunity,
    status_code=status.HTTP_201_CREATED,
    summary="Save one verified opportunity",
)
async def save_opportunity(
    opportunity_id: UUID,
    service: Annotated[OpportunityReader, Depends(get_opportunity_service)],
) -> SavedOpportunity:
    return await service.save(opportunity_id)


@router.delete(
    "/{opportunity_id}/save",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove one saved opportunity",
)
async def remove_saved_opportunity(
    opportunity_id: UUID,
    service: Annotated[OpportunityReader, Depends(get_opportunity_service)],
) -> Response:
    await service.remove_save(opportunity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/saved",
    response_model=SavedOpportunityListResponse,
    summary="List owner-scoped saved opportunities",
)
async def list_saved_opportunities(
    service: Annotated[OpportunityReader, Depends(get_opportunity_service)],
) -> SavedOpportunityListResponse:
    return await service.list_saved()
