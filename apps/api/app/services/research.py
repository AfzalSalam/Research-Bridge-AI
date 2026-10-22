from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.errors import AppError
from app.db.models.research import ResearchItem
from app.db.models.workflow import OutreachDraft
from app.relevance.mentor import RelevanceWeights, derive_candidates
from app.repositories.research import ResearchRepository
from app.schemas.mentor_discovery import MentorCandidate
from app.schemas.research import (
    DraftSummary,
    RecipientUpdate,
    ResearchResult,
    ResearchSave,
)
from app.services.mentor_discovery import _candidate_response
from app.services.profile import ProfileReader


class ResearchService:
    def __init__(
        self, repository: ResearchRepository, profiles: ProfileReader, owner: UUID
    ) -> None:
        self.repository, self.profiles, self.owner = repository, profiles, owner

    async def selection(
        self, author_id: UUID, paper_ids: list[UUID], query: str
    ) -> MentorCandidate:
        papers = [await self.repository.paper(p) for p in paper_ids]
        if not papers or any(
            not any(a.id == author_id for a in p.authors) for p in papers
        ):
            raise AppError(
                code="invalid_authorship",
                message="Choose an author credited on every selected paper.",
                status_code=422,
            )
        profile = await self.profiles.get_profile()
        derived = derive_candidates(
            query=query,
            query_kind="text",
            papers=papers,
            profile=profile,
            evaluation_year=datetime.now(UTC).year,
            weights=RelevanceWeights(),
        )
        return next(
            _candidate_response(c) for c in derived.candidates if c.id == author_id
        )

    async def save(self, paper_id: UUID, body: ResearchSave) -> ResearchResult:
        paper = await self.repository.paper(paper_id)
        if not set(body.author_ids).issubset({a.id for a in paper.authors}):
            raise AppError(
                code="invalid_authorship",
                message="Shortlist authors of the selected paper.",
                status_code=422,
            )
        item = await self.repository.item(self.owner, paper_id)
        if item is None:
            item = ResearchItem(owner_id=self.owner, paper_id=paper_id)
            self.repository.session.add(item)
        if "collection" in body.model_fields_set or item.collection is None:
            item.collection = body.collection
        if "note" in body.model_fields_set or item.note is None:
            item.note = body.note
        if "author_ids" in body.model_fields_set or item.author_ids is None:
            item.author_ids = [str(a) for a in dict.fromkeys(body.author_ids)]
        await self.repository.session.flush()
        await self.repository.session.refresh(item)
        return ResearchResult(
            id=item.id,
            paper=paper,
            collection=item.collection,
            note=item.note,
            author_ids=[UUID(a) for a in item.author_ids],
            updated_at=item.updated_at,
        )

    async def list_items(self) -> list[ResearchResult]:
        return [
            ResearchResult(
                id=item.id,
                paper=await self.repository.paper(item.paper_id),
                collection=item.collection,
                note=item.note,
                author_ids=[UUID(a) for a in item.author_ids],
                updated_at=item.updated_at,
            )
            for item in await self.repository.items(self.owner)
        ]

    async def drafts(self) -> list[DraftSummary]:
        drafts = await self.repository.session.scalars(
            select(OutreachDraft)
            .where(OutreachDraft.owner_id == self.owner)
            .order_by(OutreachDraft.updated_at.desc())
            .limit(200)
        )
        return [
            DraftSummary(
                id=d.id,
                mentor_id=d.recipient_author_id,
                recipient_display_name=d.recipient_display_name,
                recipient_contact=d.recipient_contact,
                subject=d.subject,
                draft_version=d.draft_version,
                updated_at=d.updated_at,
            )
            for d in drafts
        ]

    async def recipient(self, draft_id: UUID, body: RecipientUpdate) -> None:
        draft = await self.repository.session.scalar(
            select(OutreachDraft)
            .where(OutreachDraft.id == draft_id, OutreachDraft.owner_id == self.owner)
            .with_for_update()
        )
        if draft is None:
            raise AppError(
                code="draft_not_found", message="Draft not found.", status_code=404
            )
        if draft.draft_version != body.expected_version:
            raise AppError(
                code="draft_version_conflict",
                message="Reload the latest draft before selecting its recipient.",
                status_code=409,
            )
        from app.repositories.contact import ContactRepository

        contact = (
            await ContactRepository(self.repository.session).cached(
                draft.recipient_author_id
            )
            if draft.recipient_author_id
            else None
        )
        match = (
            next(
                (
                    e
                    for e in contact.emails
                    if e.email.casefold() == body.email.casefold()
                ),
                None,
            )
            if contact and contact.status == "found"
            else None
        )
        if match:
            provenance = {
                "kind": "official-profile",
                "sourceUrl": match.source_url,
                "checkedAt": match.checked_at.isoformat(),
            }
        elif body.manually_confirmed:
            provenance = {
                "kind": "student-provided",
                "sourceUrl": "",
                "checkedAt": datetime.now(UTC).isoformat(),
            }
        else:
            raise AppError(
                code="recipient_confirmation_required",
                message="Confirm this address is yours to provide and is unverified.",
                status_code=422,
            )
        draft.recipient_contact = body.email.strip().lower()
        draft.contact_provenance = provenance
        draft.reviewed_at = None
        draft.draft_version += 1
        from app.db.models.workflow import OutreachDraftRevision

        self.repository.session.add(
            OutreachDraftRevision(
                draft_id=draft.id,
                editor_owner_id=self.owner,
                version=draft.draft_version,
                subject=draft.subject,
                body=draft.body,
                claim_evidence=draft.claim_evidence,
                evidence_map_status=draft.evidence_map_status,
            )
        )
        await self.repository.session.flush()
