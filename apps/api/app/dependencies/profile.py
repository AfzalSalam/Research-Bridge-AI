from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.dependencies.database import get_session
from app.repositories.owners import SqlAlchemyOwnerRepository
from app.repositories.profiles import SqlAlchemyProfileRepository
from app.services.profile import ProfileService


def get_profile_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileService:
    """Build the profile service from request-scoped repositories."""

    settings = cast(Settings, request.app.state.settings)
    return ProfileService(
        owner_id=settings.demo_owner_id,
        owners=SqlAlchemyOwnerRepository(session),
        profiles=SqlAlchemyProfileRepository(session),
    )
