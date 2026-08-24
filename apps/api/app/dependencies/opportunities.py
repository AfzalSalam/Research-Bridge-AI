from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
    get_optional_principal,
)
from app.dependencies.database import get_session
from app.providers.opportunities import (
    OPPORTUNITY_SOURCES,
    OpportunityProvider,
)
from app.repositories.opportunities import SqlAlchemyOpportunityRepository
from app.runtime import OpportunityRuntime
from app.services.applications import (
    ApplicationTrackerReader,
    ApplicationTrackerService,
)
from app.services.opportunities import OpportunityReader, OpportunityService


def _get_opportunity_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    owner_id: UUID | None,
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
        owner_id=owner_id,
        repository=repository,
        provider=provider,
        sources=[OPPORTUNITY_SOURCES[key] for key in settings.greenhouse_board_keys],
        stale_after_hours=settings.opportunity_stale_after_hours,
    )


def get_opportunity_search_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[
        AuthenticatedPrincipal | None, Depends(get_optional_principal)
    ],
) -> OpportunityReader:
    """Compose public search with optional signed-in saved-state enrichment."""

    return _get_opportunity_service(
        request,
        session,
        principal.owner_id if principal is not None else None,
    )


def get_opportunity_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> OpportunityReader:
    """Compose an authenticated saved-opportunity service."""

    return _get_opportunity_service(request, session, principal.owner_id)


def get_application_tracker_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> ApplicationTrackerReader:
    """Compose owner-scoped application tracking without external submission."""

    return ApplicationTrackerService(
        owner_id=principal.owner_id,
        repository=SqlAlchemyOpportunityRepository(session),
    )
