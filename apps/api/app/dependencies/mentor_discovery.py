from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import Depends, Request

from app.core.config import Settings
from app.dependencies.account_profile import get_account_profile_service
from app.dependencies.discovery import get_paper_discovery_service
from app.relevance.mentor import RelevanceWeights
from app.services.account_profile import AccountProfileService
from app.services.discovery import PaperDiscoveryReader
from app.services.mentor_discovery import MentorDiscoveryReader, MentorDiscoveryService


def get_mentor_discovery_service(
    request: Request,
    papers: Annotated[PaperDiscoveryReader, Depends(get_paper_discovery_service)],
    profiles: Annotated[AccountProfileService, Depends(get_account_profile_service)],
) -> MentorDiscoveryReader:
    """Compose mentor discovery from existing request-scoped services."""

    settings = cast(Settings, request.app.state.settings)
    return MentorDiscoveryService(
        papers=papers,
        profiles=profiles,
        weights=RelevanceWeights(
            query_evidence=settings.mentor_query_evidence_weight,
            profile_alignment=settings.mentor_profile_alignment_weight,
            supporting_depth=settings.mentor_supporting_depth_weight,
            recent_activity=settings.mentor_recent_activity_weight,
            evidence_completeness=settings.mentor_evidence_completeness_weight,
        ),
        evaluation_year=datetime.now(UTC).year,
    )
