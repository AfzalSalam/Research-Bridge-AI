from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.academic import Paper
from app.db.models.enums import DraftGenerationMode
from app.db.models.workflow import DraftPaper, OutreachDraft, OutreachDraftRevision
from app.outreach.drafting import FallbackReason, GroundedDraft


class DraftNotFoundError(Exception):
    """The draft is absent or outside the current owner scope."""


class DraftVersionConflictError(Exception):
    """The editor tried to overwrite a newer persisted revision."""


@dataclass(frozen=True, slots=True)
class NewOutreachDraft:
    owner_id: UUID
    mentor_id: UUID
    recipient_display_name: str
    paper_ids: tuple[UUID, ...]
    grounded: GroundedDraft
    generation_mode: DraftGenerationMode
    prompt_version: str | None
    template_version: str
    provider: str | None
    model_name: str | None
    fallback_reason: FallbackReason | None


class OutreachRepository(Protocol):
    async def create(self, values: NewOutreachDraft) -> OutreachDraft: ...

    async def get_by_id(self, owner_id: UUID, draft_id: UUID) -> OutreachDraft: ...

    async def update(
        self,
        *,
        owner_id: UUID,
        draft_id: UUID,
        expected_version: int,
        subject: str,
        body: str,
    ) -> OutreachDraft: ...


class SqlAlchemyOutreachRepository:
    """Owner-scoped latest snapshot plus immutable revision persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, values: NewOutreachDraft) -> OutreachDraft:
        fact_payload = [
            fact.model_dump(mode="json", by_alias=True)
            for fact in values.grounded.selected_student_facts
        ]
        claim_payload = [
            claim.model_dump(mode="json", by_alias=True)
            for claim in values.grounded.claim_evidence
        ]
        draft = OutreachDraft(
            owner_id=values.owner_id,
            recipient_author_id=values.mentor_id,
            recipient_display_name=values.recipient_display_name,
            recipient_contact=None,
            subject=values.grounded.subject,
            body=values.grounded.body,
            selected_student_facts=fact_payload,
            claim_evidence=claim_payload,
            uncertainty_warnings=list(values.grounded.uncertainty_warnings),
            evidence_map_status="verified-generated",
            generation_mode=values.generation_mode,
            template_version=values.template_version,
            prompt_version=values.prompt_version,
            provider=values.provider,
            model_name=values.model_name,
            fallback_reason=values.fallback_reason,
            reviewed_at=None,
            draft_version=1,
        )
        draft.paper_links = [
            DraftPaper(paper_id=paper_id, position=position)
            for position, paper_id in enumerate(values.paper_ids)
        ]
        draft.revisions = [
            OutreachDraftRevision(
                editor_owner_id=values.owner_id,
                version=1,
                subject=values.grounded.subject,
                body=values.grounded.body,
                claim_evidence=claim_payload,
                evidence_map_status="verified-generated",
            )
        ]
        self._session.add(draft)
        await self._session.flush()
        return await self.get_by_id(values.owner_id, draft.id)

    async def get_by_id(self, owner_id: UUID, draft_id: UUID) -> OutreachDraft:
        draft = await self._session.scalar(
            _draft_statement().where(
                OutreachDraft.id == draft_id,
                OutreachDraft.owner_id == owner_id,
            )
        )
        if draft is None:
            raise DraftNotFoundError
        return draft

    async def update(
        self,
        *,
        owner_id: UUID,
        draft_id: UUID,
        expected_version: int,
        subject: str,
        body: str,
    ) -> OutreachDraft:
        draft = await self._session.scalar(
            _draft_statement()
            .where(
                OutreachDraft.id == draft_id,
                OutreachDraft.owner_id == owner_id,
            )
            .with_for_update()
        )
        if draft is None:
            raise DraftNotFoundError
        if draft.draft_version != expected_version:
            raise DraftVersionConflictError

        next_version = expected_version + 1
        draft.subject = subject
        draft.body = body
        draft.evidence_map_status = "manual-edit-needs-review"
        draft.reviewed_at = None
        draft.draft_version = next_version
        draft.revisions.append(
            OutreachDraftRevision(
                editor_owner_id=owner_id,
                version=next_version,
                subject=subject,
                body=body,
                claim_evidence=draft.claim_evidence,
                evidence_map_status="manual-edit-needs-review",
            )
        )
        await self._session.flush()
        return await self.get_by_id(owner_id, draft_id)


def _draft_statement() -> Select[tuple[OutreachDraft]]:
    return select(OutreachDraft).options(
        selectinload(OutreachDraft.recipient_author),
        selectinload(OutreachDraft.paper_links)
        .selectinload(DraftPaper.paper)
        .selectinload(Paper.topics),
        selectinload(OutreachDraft.revisions),
    )
