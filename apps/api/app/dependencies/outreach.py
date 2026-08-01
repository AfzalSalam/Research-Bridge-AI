from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.dependencies.database import get_session
from app.dependencies.mentor_discovery import get_mentor_discovery_service
from app.dependencies.profile import get_profile_service
from app.outreach.drafting import OutreachDraftGenerator
from app.repositories.outreach import SqlAlchemyOutreachRepository
from app.repositories.owners import SqlAlchemyOwnerRepository
from app.runtime import OutreachRuntime
from app.services.mentor_discovery import MentorDiscoveryReader
from app.services.outreach import OutreachReader, OutreachService
from app.services.profile import ProfileReader


def get_outreach_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    mentors: Annotated[MentorDiscoveryReader, Depends(get_mentor_discovery_service)],
    profiles: Annotated[ProfileReader, Depends(get_profile_service)],
) -> OutreachReader:
    """Compose live outreach from server-owned evidence and optional generation."""

    settings = cast(Settings, request.app.state.settings)
    runtime = cast(OutreachRuntime, request.app.state.outreach_runtime)
    override = request.app.state.outreach_generator_override
    generator = (
        cast(OutreachDraftGenerator, override)
        if override is not None
        else runtime.provider
    )
    return OutreachService(
        owner_id=settings.demo_owner_id,
        owners=SqlAlchemyOwnerRepository(session),
        repository=SqlAlchemyOutreachRepository(session),
        mentors=mentors,
        profiles=profiles,
        generator=generator,
    )
