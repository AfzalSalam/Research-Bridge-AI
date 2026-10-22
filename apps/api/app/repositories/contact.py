from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import (
    Author,
    Institution,
    Paper,
    PaperAuthor,
    PaperAuthorInstitution,
)
from app.db.models.contact import PublicContactLookup
from app.schemas.contact import ContactLookupResponse


@dataclass(frozen=True)
class ContactIdentity:
    id: UUID
    name: str
    orcid: str | None
    affiliations: tuple[str, ...]
    papers: tuple[tuple[str, str | None], ...]
    ror_ids: tuple[str, ...] = ()


class ContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def identity(self, author_id: UUID) -> ContactIdentity | None:
        author = await self.session.get(Author, author_id)
        if author is None:
            return None
        papers = (
            await self.session.execute(
                select(Paper.title, Paper.doi)
                .join(PaperAuthor)
                .where(
                    PaperAuthor.author_id == author_id, Paper.is_retracted.is_(False)
                )
                .order_by(Paper.publication_year.desc())
                .limit(40)
            )
        ).all()
        names = (
            await self.session.scalars(
                select(Institution.display_name)
                .join(PaperAuthorInstitution)
                .where(PaperAuthorInstitution.author_id == author_id)
                .distinct()
                .limit(30)
            )
        ).all()
        ror_ids = (
            await self.session.scalars(
                select(Institution.ror_id)
                .join(PaperAuthorInstitution)
                .where(
                    PaperAuthorInstitution.author_id == author_id,
                    Institution.ror_id.is_not(None),
                )
                .distinct()
                .limit(6)
            )
        ).all()
        return ContactIdentity(
            author.id,
            author.display_name,
            author.orcid,
            tuple(names),
            tuple((row[0], row[1]) for row in papers),
            tuple(identifier for identifier in ror_ids if identifier),
        )

    async def cached(self, author_id: UUID) -> ContactLookupResponse | None:
        record = await self.session.scalar(
            select(PublicContactLookup)
            .where(PublicContactLookup.author_id == author_id)
            .order_by(PublicContactLookup.checked_at.desc())
            .limit(1)
        )
        return ContactLookupResponse.model_validate(record.payload) if record else None

    async def save(self, result: ContactLookupResponse) -> None:
        self.session.add(
            PublicContactLookup(
                author_id=result.author_id,
                checked_at=result.checked_at,
                payload=result.model_dump(mode="json"),
            )
        )
        await self.session.flush()
