from datetime import UTC
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.db.models.academic import Paper, PaperAuthor, PaperAuthorInstitution
from app.db.models.research import ResearchItem
from app.schemas.discovery import DiscoveredPaper, PaperInstitution, PaperTopic
from app.schemas.discovery import PaperAuthor as AuthorResult


class ResearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def paper(self, paper_id: UUID) -> DiscoveredPaper:
        paper = await self.session.scalar(
            select(Paper)
            .where(Paper.id == paper_id, Paper.is_retracted.is_(False))
            .options(
                selectinload(Paper.author_links).selectinload(PaperAuthor.author),
                selectinload(Paper.author_links)
                .selectinload(PaperAuthor.institution_links)
                .selectinload(PaperAuthorInstitution.institution),
                selectinload(Paper.topics),
            )
        )
        if paper is None or not paper.openalex_id:
            raise AppError(
                code="paper_not_found",
                message="Paper unavailable. Resolve the citation first.",
                status_code=404,
            )
        return DiscoveredPaper(
            id=paper.id,
            openalex_id=paper.openalex_id,
            doi=paper.doi,
            title=paper.title,
            publication_year=paper.publication_year,
            publication_date=paper.publication_date,
            work_type=paper.work_type,
            language=paper.language,
            venue=paper.venue,
            abstract_excerpt=paper.abstract,
            evidence_strength="full-abstract" if paper.abstract else "title-only",
            source_url=paper.primary_source_url,
            last_verified_at=(
                paper.last_verified_at.replace(tzinfo=UTC)
                if paper.last_verified_at.tzinfo is None
                else paper.last_verified_at
            ),
            authors=[
                AuthorResult(
                    id=link.author.id,
                    openalex_id=link.author.openalex_id,
                    orcid=link.author.orcid,
                    display_name=link.author.display_name,
                    is_corresponding=link.is_corresponding,
                    source_url=link.author.source_url,
                    institutions=[
                        PaperInstitution(
                            id=x.institution.id,
                            openalex_id=x.institution.openalex_id,
                            ror_id=x.institution.ror_id,
                            display_name=x.institution.display_name,
                            country_code=x.institution.country_code,
                            city=x.institution.city,
                            source_url=x.institution.source_url,
                        )
                        for x in link.institution_links
                    ],
                )
                for link in paper.author_links
            ],
            topics=[
                PaperTopic(
                    id=t.id,
                    openalex_id=t.openalex_topic_id,
                    display_name=t.topic,
                    score=t.score,
                )
                for t in paper.topics
            ],
        )

    async def items(self, owner: UUID) -> list[ResearchItem]:
        return list(
            await self.session.scalars(
                select(ResearchItem)
                .where(ResearchItem.owner_id == owner)
                .order_by(ResearchItem.updated_at.desc())
                .limit(200)
            )
        )

    async def item(self, owner: UUID, paper: UUID) -> ResearchItem | None:
        result = await self.session.scalar(
            select(ResearchItem)
            .where(ResearchItem.owner_id == owner, ResearchItem.paper_id == paper)
            .with_for_update()
        )

        return result if isinstance(result, ResearchItem) else None
