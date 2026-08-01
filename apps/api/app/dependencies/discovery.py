from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_session
from app.providers.base import AcademicPaperProvider
from app.repositories.academic import SqlAlchemyAcademicRepository
from app.runtime import DiscoveryRuntime
from app.services.discovery import PaperDiscoveryReader, PaperDiscoveryService


def get_paper_discovery_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaperDiscoveryReader:
    """Compose live discovery while retaining an explicit provider test seam."""

    runtime = cast(DiscoveryRuntime, request.app.state.discovery_runtime)
    override = request.app.state.paper_provider_override
    provider = (
        cast(AcademicPaperProvider, override)
        if override is not None
        else runtime.provider
    )
    return PaperDiscoveryService(
        provider=provider,
        repository=SqlAlchemyAcademicRepository(session),
        cache=runtime.cache,
    )
