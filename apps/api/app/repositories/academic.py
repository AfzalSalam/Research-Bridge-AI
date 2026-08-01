from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.academic import (
    Author,
    Institution,
    Paper,
    PaperAuthor,
    PaperAuthorInstitution,
    PaperTopic,
    ProvenanceRecord,
)
from app.db.models.enums import EvidenceStrength, PublicEntityKind
from app.providers.base import (
    NormalizedAuthor,
    NormalizedInstitution,
    NormalizedPaper,
    NormalizedTopic,
)


@dataclass(frozen=True, slots=True)
class StoredInstitution:
    id: UUID
    value: NormalizedInstitution


@dataclass(frozen=True, slots=True)
class StoredAuthor:
    id: UUID
    value: NormalizedAuthor
    institutions: tuple[StoredInstitution, ...]


@dataclass(frozen=True, slots=True)
class StoredTopic:
    id: UUID
    value: NormalizedTopic


@dataclass(frozen=True, slots=True)
class StoredPaper:
    id: UUID
    value: NormalizedPaper
    authors: tuple[StoredAuthor, ...]
    topics: tuple[StoredTopic, ...]


class AcademicRepository(Protocol):
    async def persist_papers(
        self, papers: tuple[NormalizedPaper, ...], *, retrieved_at: datetime
    ) -> tuple[StoredPaper, ...]: ...


class SqlAlchemyAcademicRepository:
    """Idempotently persist normalized academic evidence in one transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._institutions: dict[
            tuple[str | None, str | None, str, str | None], Institution
        ] = {}
        self._authors: dict[tuple[str | None, str | None, str], Author] = {}

    async def persist_papers(
        self, papers: tuple[NormalizedPaper, ...], *, retrieved_at: datetime
    ) -> tuple[StoredPaper, ...]:
        stored: list[StoredPaper] = []
        for normalized in papers:
            stored.append(await self._persist_paper(normalized, retrieved_at))
        await self._session.flush()
        return tuple(stored)

    async def _persist_paper(
        self, normalized: NormalizedPaper, retrieved_at: datetime
    ) -> StoredPaper:
        paper = await self._find_paper(normalized)
        if paper is None:
            paper = Paper(
                title=normalized.title,
                normalized_title=normalized.normalized_title,
                publication_year=normalized.publication_year,
                publication_date=normalized.publication_date,
                work_type=normalized.work_type,
                language=normalized.language,
                is_retracted=normalized.is_retracted,
                venue=normalized.venue,
                abstract=normalized.abstract,
                doi=normalized.doi,
                openalex_id=normalized.openalex_id,
                evidence_strength=_database_evidence(normalized),
                primary_source_url=normalized.source_url,
                last_verified_at=retrieved_at,
            )
            self._session.add(paper)
            await self._session.flush()
        else:
            _apply_paper_values(paper, normalized, retrieved_at)
            paper.author_links.clear()
            paper.topics.clear()
            await self._session.flush()

        stored_authors: list[StoredAuthor] = []
        for author_position, normalized_author in enumerate(normalized.authors):
            author = await self._resolve_author(normalized_author, retrieved_at)
            paper_author = PaperAuthor(
                paper=paper,
                author=author,
                position=author_position,
                is_corresponding=normalized_author.is_corresponding,
                institution_links=[],
            )
            self._session.add(paper_author)
            stored_institutions: list[StoredInstitution] = []
            for institution_position, normalized_institution in enumerate(
                normalized_author.institutions
            ):
                institution = await self._resolve_institution(
                    normalized_institution, retrieved_at
                )
                paper_author.institution_links.append(
                    PaperAuthorInstitution(
                        institution=institution,
                        position=institution_position,
                    )
                )
                stored_institutions.append(
                    StoredInstitution(id=institution.id, value=normalized_institution)
                )
            stored_authors.append(
                StoredAuthor(
                    id=author.id,
                    value=normalized_author,
                    institutions=tuple(stored_institutions),
                )
            )

        stored_topics: list[StoredTopic] = []
        for position, normalized_topic in enumerate(normalized.topics):
            topic = PaperTopic(
                paper=paper,
                topic=normalized_topic.display_name,
                normalized_topic=normalized_topic.normalized_name,
                openalex_topic_id=normalized_topic.openalex_id,
                score=normalized_topic.score,
                position=position,
            )
            self._session.add(topic)
            await self._session.flush()
            stored_topics.append(StoredTopic(id=topic.id, value=normalized_topic))

        await self._upsert_provenance(
            entity_kind=PublicEntityKind.PAPER,
            entity_id=paper.id,
            source_record_id=normalized.openalex_id,
            source_url=normalized.source_url,
            retrieved_at=retrieved_at,
            content_hash=normalized.content_hash,
            fields=[
                "title",
                "publication_year",
                "publication_date",
                "type",
                "language",
                "is_retracted",
                "venue",
                "abstract",
                "doi",
                "authorships",
                "topics",
            ],
        )
        await self._session.flush()
        return StoredPaper(
            id=paper.id,
            value=normalized,
            authors=tuple(stored_authors),
            topics=tuple(stored_topics),
        )

    async def _find_paper(self, normalized: NormalizedPaper) -> Paper | None:
        statement = _paper_statement().where(
            Paper.openalex_id == normalized.openalex_id
        )
        paper: Paper | None = await self._session.scalar(statement)
        if paper is not None:
            return paper
        if normalized.doi:
            paper = await self._session.scalar(
                _paper_statement().where(Paper.doi == normalized.doi)
            )
            if paper is not None:
                return paper
        fallback: Paper | None = await self._session.scalar(
            _paper_statement().where(
                Paper.normalized_title == normalized.normalized_title,
                Paper.publication_year == normalized.publication_year,
                Paper.openalex_id.is_(None),
                Paper.doi.is_(None),
            )
        )
        return fallback

    async def _resolve_author(
        self, normalized: NormalizedAuthor, retrieved_at: datetime
    ) -> Author:
        identity = (
            normalized.openalex_id,
            normalized.orcid,
            normalized.normalized_name,
        )
        cached = self._authors.get(identity)
        if cached is not None:
            _apply_author_values(cached, normalized, retrieved_at)
            return cached

        author = None
        if normalized.openalex_id:
            author = await self._session.scalar(
                select(Author).where(Author.openalex_id == normalized.openalex_id)
            )
        if author is None and normalized.orcid:
            author = await self._session.scalar(
                select(Author).where(Author.orcid == normalized.orcid)
            )
        if (
            author is None
            and normalized.openalex_id is None
            and normalized.orcid is None
        ):
            author = await self._session.scalar(
                select(Author).where(
                    Author.normalized_name == normalized.normalized_name,
                    Author.openalex_id.is_(None),
                    Author.orcid.is_(None),
                )
            )
        if author is None:
            author = Author(
                display_name=normalized.display_name,
                normalized_name=normalized.normalized_name,
                orcid=normalized.orcid,
                openalex_id=normalized.openalex_id,
                source_url=normalized.source_url,
                last_verified_at=retrieved_at,
            )
            self._session.add(author)
            await self._session.flush()
        else:
            _apply_author_values(author, normalized, retrieved_at)
        self._authors[identity] = author
        await self._upsert_provenance(
            entity_kind=PublicEntityKind.AUTHOR,
            entity_id=author.id,
            source_record_id=(
                normalized.openalex_id
                or normalized.orcid
                or f"name:{normalized.normalized_name[:240]}"
            ),
            source_url=normalized.source_url,
            retrieved_at=retrieved_at,
            content_hash=normalized.content_hash,
            fields=["display_name", "orcid"],
        )
        return author

    async def _resolve_institution(
        self, normalized: NormalizedInstitution, retrieved_at: datetime
    ) -> Institution:
        identity = (
            normalized.openalex_id,
            normalized.ror_id,
            normalized.normalized_name,
            normalized.country_code,
        )
        cached = self._institutions.get(identity)
        if cached is not None:
            _apply_institution_values(cached, normalized, retrieved_at)
            return cached

        institution = None
        if normalized.openalex_id:
            institution = await self._session.scalar(
                select(Institution).where(
                    Institution.openalex_id == normalized.openalex_id
                )
            )
        if institution is None and normalized.ror_id:
            institution = await self._session.scalar(
                select(Institution).where(Institution.ror_id == normalized.ror_id)
            )
        if institution is None:
            institution = await self._session.scalar(
                select(Institution).where(
                    Institution.normalized_name == normalized.normalized_name,
                    Institution.country_code == normalized.country_code,
                    Institution.openalex_id.is_(None),
                    Institution.ror_id.is_(None),
                )
            )
        if institution is None:
            institution = Institution(
                display_name=normalized.display_name,
                normalized_name=normalized.normalized_name,
                country_code=normalized.country_code,
                city=normalized.city,
                ror_id=normalized.ror_id,
                openalex_id=normalized.openalex_id,
                source_url=normalized.source_url,
                last_verified_at=retrieved_at,
            )
            self._session.add(institution)
            await self._session.flush()
        else:
            _apply_institution_values(institution, normalized, retrieved_at)
        self._institutions[identity] = institution
        await self._upsert_provenance(
            entity_kind=PublicEntityKind.INSTITUTION,
            entity_id=institution.id,
            source_record_id=(
                normalized.openalex_id
                or normalized.ror_id
                or f"name:{normalized.normalized_name[:240]}"
            ),
            source_url=normalized.source_url,
            retrieved_at=retrieved_at,
            content_hash=normalized.content_hash,
            fields=["display_name", "ror", "country_code", "city"],
        )
        return institution

    async def _upsert_provenance(
        self,
        *,
        entity_kind: PublicEntityKind,
        entity_id: UUID,
        source_record_id: str,
        source_url: str,
        retrieved_at: datetime,
        content_hash: str,
        fields: list[str],
    ) -> None:
        record = await self._session.scalar(
            select(ProvenanceRecord).where(
                ProvenanceRecord.entity_kind == entity_kind,
                ProvenanceRecord.entity_id == entity_id,
                ProvenanceRecord.source_name == "OpenAlex",
                ProvenanceRecord.source_record_id == source_record_id,
            )
        )
        if record is None:
            self._session.add(
                ProvenanceRecord(
                    entity_kind=entity_kind,
                    entity_id=entity_id,
                    source_name="OpenAlex",
                    source_record_id=source_record_id,
                    source_url=source_url,
                    retrieved_at=retrieved_at,
                    last_verified_at=retrieved_at,
                    content_hash=content_hash,
                    fields=fields,
                )
            )
            return
        record.source_url = source_url
        record.last_verified_at = retrieved_at
        record.content_hash = content_hash
        record.fields = fields


def _paper_statement() -> Select[tuple[Paper]]:
    return select(Paper).options(
        selectinload(Paper.author_links)
        .selectinload(PaperAuthor.institution_links)
        .selectinload(PaperAuthorInstitution.institution),
        selectinload(Paper.topics),
    )


def _database_evidence(paper: NormalizedPaper) -> EvidenceStrength:
    return (
        EvidenceStrength.ABSTRACT
        if paper.evidence_strength == "full-abstract"
        else EvidenceStrength.TITLE_ONLY
    )


def _apply_paper_values(
    target: Paper, source: NormalizedPaper, retrieved_at: datetime
) -> None:
    target.title = source.title
    target.normalized_title = source.normalized_title
    target.publication_year = source.publication_year
    target.publication_date = source.publication_date or target.publication_date
    target.work_type = source.work_type or target.work_type
    target.language = source.language or target.language
    target.is_retracted = source.is_retracted
    target.venue = source.venue or target.venue
    target.abstract = source.abstract or target.abstract
    target.doi = source.doi or target.doi
    target.openalex_id = source.openalex_id
    target.evidence_strength = (
        EvidenceStrength.ABSTRACT if target.abstract else EvidenceStrength.TITLE_ONLY
    )
    target.primary_source_url = source.source_url
    target.last_verified_at = retrieved_at


def _apply_author_values(
    target: Author, source: NormalizedAuthor, retrieved_at: datetime
) -> None:
    target.display_name = source.display_name
    target.normalized_name = source.normalized_name
    target.orcid = source.orcid or target.orcid
    target.openalex_id = source.openalex_id or target.openalex_id
    target.source_url = source.source_url
    target.last_verified_at = retrieved_at


def _apply_institution_values(
    target: Institution, source: NormalizedInstitution, retrieved_at: datetime
) -> None:
    target.display_name = source.display_name
    target.normalized_name = source.normalized_name
    target.country_code = source.country_code or target.country_code
    target.city = source.city or target.city
    target.ror_id = source.ror_id or target.ror_id
    target.openalex_id = source.openalex_id or target.openalex_id
    target.source_url = source.source_url
    target.last_verified_at = retrieved_at
