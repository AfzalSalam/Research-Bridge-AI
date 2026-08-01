from typing import Annotated, cast

from fastapi import Depends, Request

from app.dependencies.profile import get_profile_service
from app.services.demo import DemoService
from app.services.mock_demo import MockDemoService
from app.services.profile import ProfileService


def get_demo_service(
    request: Request,
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> DemoService:
    """Compose the demo service while retaining an explicit test override."""

    override = request.app.state.demo_service_override
    if override is not None:
        return cast(DemoService, override)
    return MockDemoService(profile_reader=profile_service)
