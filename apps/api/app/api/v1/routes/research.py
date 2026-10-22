from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.account_profile import get_account_profile_service
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.database import get_session
from app.repositories.research import ResearchRepository
from app.schemas.discovery import DiscoveredPaper
from app.schemas.mentor_discovery import MentorCandidate
from app.schemas.research import (
    DraftSummary,
    RecipientUpdate,
    ResearchResult,
    ResearchSave,
)
from app.services.account_profile import AccountProfileService
from app.services.research import ResearchService

router = APIRouter(prefix="/research", tags=["research"])


def get_research_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    profiles: Annotated[AccountProfileService, Depends(get_account_profile_service)],
) -> ResearchService:
    return ResearchService(ResearchRepository(session), profiles, principal.owner_id)


Service = Annotated[ResearchService, Depends(get_research_service)]


@router.get("/papers", response_model=list[ResearchResult])
async def list_research(service: Service) -> list[ResearchResult]:
    return await service.list_items()


@router.get("/papers/{paper_id}", response_model=DiscoveredPaper)
async def read_paper(paper_id: UUID, service: Service) -> DiscoveredPaper:
    return await service.repository.paper(paper_id)


@router.put("/papers/{paper_id}", response_model=ResearchResult)
async def save_paper(
    paper_id: UUID, body: ResearchSave, service: Service
) -> ResearchResult:
    return await service.save(paper_id, body)


@router.get("/papers/{paper_id}/authors/{author_id}", response_model=MentorCandidate)
async def select_author(
    paper_id: UUID, author_id: UUID, service: Service
) -> MentorCandidate:
    paper = await service.repository.paper(paper_id)
    return await service.selection(author_id, [paper_id], paper.title[:300])


@router.get("/drafts", response_model=list[DraftSummary])
async def list_drafts(service: Service) -> list[DraftSummary]:
    return await service.drafts()


@router.put("/drafts/{draft_id}/recipient", status_code=204)
async def select_recipient(
    draft_id: UUID, body: RecipientUpdate, service: Service
) -> Response:
    await service.recipient(draft_id, body)
    return Response(status_code=204)
