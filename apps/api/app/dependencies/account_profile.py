"""Authenticated-account profile dependency composition."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.database import get_session
from app.repositories.profiles import SqlAlchemyProfileRepository
from app.services.account_profile import AccountProfileService


def get_account_profile_service(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountProfileService:
    """Build an account profile service scoped by the verified principal."""

    return AccountProfileService(
        owner_id=principal.owner_id,
        profiles=SqlAlchemyProfileRepository(session),
    )
