from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.dependencies.profile import get_profile_service
from app.schemas.demo import StudentProfile
from app.schemas.errors import ErrorResponse
from app.services.profile import ProfileService

router = APIRouter(prefix="/demo/profile", tags=["demo"])
error_responses: dict[int | str, dict[str, Any]] = {
    422: {
        "model": ErrorResponse,
        "description": "The profile could not be validated.",
    },
    500: {
        "model": ErrorResponse,
        "description": "The profile database operation failed.",
    },
}


@router.get(
    "",
    response_model=StudentProfile,
    responses={500: error_responses[500]},
    summary="Read the durable fictional demo profile",
)
async def read_demo_profile(
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> StudentProfile:
    return await service.get_profile()


@router.put(
    "",
    response_model=StudentProfile,
    responses=error_responses,
    summary="Save the fictional demo profile",
)
async def update_demo_profile(
    profile: StudentProfile,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> StudentProfile:
    return await service.save_profile(profile)
