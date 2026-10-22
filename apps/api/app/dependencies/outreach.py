from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.account_profile import get_account_profile_service
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.database import get_session
from app.dependencies.mentor_discovery import get_mentor_discovery_service
from app.outreach.drafting import OutreachDraftGenerator
from app.repositories.outreach import SqlAlchemyOutreachRepository
from app.repositories.research import ResearchRepository
from app.runtime import OutreachRuntime
from app.services.account_profile import AccountProfileService
from app.services.mentor_discovery import MentorDiscoveryReader
from app.services.outreach import OutreachReader, OutreachService
from app.services.research import ResearchService


def get_outreach_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    mentors: Annotated[MentorDiscoveryReader, Depends(get_mentor_discovery_service)],
    profiles: Annotated[AccountProfileService, Depends(get_account_profile_service)],
) -> OutreachReader:
    """Compose live outreach from server-owned evidence and optional generation."""

    runtime = cast(OutreachRuntime, request.app.state.outreach_runtime)
    override = request.app.state.outreach_generator_override
    generator = (
        cast(OutreachDraftGenerator, override)
        if override is not None
        else runtime.provider
    )
    return OutreachService(
        owner_id=principal.owner_id,
        repository=SqlAlchemyOutreachRepository(session),
        mentors=mentors,
        profiles=profiles,
        generator=generator,
        selection=ResearchService(
            ResearchRepository(session), profiles, principal.owner_id
        ),
    )
