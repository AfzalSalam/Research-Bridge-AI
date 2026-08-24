"""Private structured student profile routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.account_profile import get_account_profile_service
from app.schemas.profile import AccountProfile, AccountProfileReadResponse
from app.services.account_profile import AccountProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get(
    "",
    response_model=AccountProfileReadResponse,
    summary="Read the signed-in student's private profile",
)
async def read_account_profile(
    service: Annotated[AccountProfileService, Depends(get_account_profile_service)],
) -> AccountProfileReadResponse:
    return AccountProfileReadResponse(profile=await service.get_optional_profile())


@router.put(
    "",
    response_model=AccountProfile,
    summary="Save the signed-in student's private profile",
)
async def update_account_profile(
    profile: AccountProfile,
    service: Annotated[AccountProfileService, Depends(get_account_profile_service)],
) -> AccountProfile:
    return await service.save_profile(profile)
