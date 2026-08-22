from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.dependencies.database import get_session
from app.providers.opportunities import (
    OPPORTUNITY_SOURCES,
    OpportunityProvider,
)
from app.repositories.opportunities import SqlAlchemyOpportunityRepository
from app.repositories.owners import SqlAlchemyOwnerRepository
from app.runtime import OpportunityRuntime
from app.services.applications import (
    ApplicationTrackerReader,
    ApplicationTrackerService,
)
from app.services.opportunities import OpportunityReader, OpportunityService


def get_opportunity_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OpportunityReader:
    """Compose verified opportunity retrieval with an explicit test seam."""

    settings = cast(Settings, request.app.state.settings)
    runtime = cast(OpportunityRuntime, request.app.state.opportunity_runtime)
    override = request.app.state.opportunity_provider_override
    provider = (
        cast(OpportunityProvider, override)
        if override is not None
        else runtime.provider
    )
    repository = SqlAlchemyOpportunityRepository(session)
    return OpportunityService(
        owner_id=settings.demo_owner_id,
        owners=SqlAlchemyOwnerRepository(session),
        repository=repository,
        provider=provider,
        sources=[OPPORTUNITY_SOURCES[key] for key in settings.greenhouse_board_keys],
        stale_after_hours=settings.opportunity_stale_after_hours,
    )


def get_application_tracker_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApplicationTrackerReader:
    """Compose owner-scoped application tracking without external submission."""

    settings = cast(Settings, request.app.state.settings)
    return ApplicationTrackerService(
        owner_id=settings.demo_owner_id,
        owners=SqlAlchemyOwnerRepository(session),
        repository=SqlAlchemyOpportunityRepository(session),
    )
