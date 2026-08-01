from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from app.core.errors import AppError
from app.db.models.enums import DraftGenerationMode
from app.db.models.workflow import OutreachDraft
from app.outreach.drafting import (
    PROMPT_VERSION,
    TEMPLATE_VERSION,
    DraftProviderError,
    FallbackReason,
    GroundingError,
    OutreachDraftGenerator,
    build_evidence_package,
    deterministic_draft,
    ground_provider_composition,
)
from app.repositories.outreach import (
    DraftNotFoundError,
    DraftVersionConflictError,
    NewOutreachDraft,
    OutreachRepository,
)
from app.repositories.owners import OwnerRepository
from app.schemas.mentor_discovery import (
    MentorCandidate,
    MentorDiscoveryRequest,
    MentorSupportingPaper,
)
from app.schemas.outreach import (
    DraftClaimEvidence,
    OutreachDraftCreateRequest,
    OutreachDraftResponse,
    OutreachDraftRevisionSummary,
    OutreachDraftUpdateRequest,
    OutreachGenerationMetadata,
    OutreachPaperEvidence,
    SelectedStudentFact,
)
from app.services.mentor_discovery import MentorDiscoveryReader
from app.services.profile import ProfileReader

logger = logging.getLogger(__name__)
_FACT_LIST_ADAPTER = TypeAdapter(list[SelectedStudentFact])
_CLAIM_LIST_ADAPTER = TypeAdapter(list[DraftClaimEvidence])


class OutreachReader(Protocol):
    async def create(
        self, request: OutreachDraftCreateRequest
    ) -> OutreachDraftResponse: ...

    async def get(self, draft_id: UUID) -> OutreachDraftResponse: ...

    async def update(
        self, draft_id: UUID, request: OutreachDraftUpdateRequest
    ) -> OutreachDraftResponse: ...


class OutreachService:
    """Verify selections, bound generation, audit grounding, and persist revisions."""

    def __init__(
        self,
        *,
        owner_id: UUID,
        owners: OwnerRepository,
        repository: OutreachRepository,
        mentors: MentorDiscoveryReader,
        profiles: ProfileReader,
        generator: OutreachDraftGenerator | None,
    ) -> None:
        self._owner_id = owner_id
        self._owners = owners
        self._repository = repository
        self._mentors = mentors
        self._profiles = profiles
        self._generator = generator

    async def create(
        self, request: OutreachDraftCreateRequest
    ) -> OutreachDraftResponse:
        discovery = await self._mentors.search(
            MentorDiscoveryRequest(
                query=request.query, paper_limit=25, candidate_limit=20
            )
        )
        mentor = next(
            (
                candidate
                for candidate in discovery.candidates
                if candidate.id == request.mentor_id
            ),
            None,
        )
        if mentor is None:
            raise AppError(
                code="outreach_mentor_not_found",
                message=(
                    "The selected researcher is not present in the verified "
                    "discovery result."
                ),
                status_code=422,
                details=[
                    {
                        "field": "mentorId",
                        "message": "Select a researcher returned for this query.",
                        "type": "value_error.outreach_mentor",
                    }
                ],
            )
        papers = _selected_papers(mentor, request.paper_ids)
        profile = await self._profiles.get_profile()
        evidence = build_evidence_package(mentor=mentor, papers=papers, profile=profile)

        fallback_reason: FallbackReason | None = None
        mode = DraftGenerationMode.DETERMINISTIC
        provider: str | None = None
        model: str | None = None
        prompt_version: str | None = None

        if request.generation_preference == "deterministic":
            fallback_reason = "deterministic-requested"
            grounded = deterministic_draft(evidence)
        elif self._generator is None:
            fallback_reason = "provider-not-configured"
            grounded = deterministic_draft(evidence)
        else:
            try:
                composition = await self._generator.generate(evidence)
                grounded = ground_provider_composition(evidence, composition)
            except DraftProviderError as error:
                fallback_reason = error.reason
                logger.warning(
                    "outreach_provider_fallback provider=%s model=%s reason=%s",
                    self._generator.name,
                    self._generator.model,
                    error.reason,
                )
                grounded = deterministic_draft(evidence)
            except GroundingError:
                fallback_reason = "grounding-check-failed"
                logger.warning(
                    "outreach_grounding_fallback provider=%s model=%s",
                    self._generator.name,
                    self._generator.model,
                )
                grounded = deterministic_draft(evidence)
            else:
                mode = DraftGenerationMode.LLM
                provider = self._generator.name
                model = self._generator.model
                prompt_version = PROMPT_VERSION

        await self._owners.get_or_create_demo(self._owner_id)
        record = await self._repository.create(
            NewOutreachDraft(
                owner_id=self._owner_id,
                mentor_id=mentor.id,
                recipient_display_name=mentor.display_name,
                paper_ids=tuple(request.paper_ids),
                grounded=grounded,
                generation_mode=mode,
                prompt_version=prompt_version,
                template_version=TEMPLATE_VERSION,
                provider=provider,
                model_name=model,
                fallback_reason=fallback_reason,
            )
        )
        return _response(record)

    async def get(self, draft_id: UUID) -> OutreachDraftResponse:
        try:
            record = await self._repository.get_by_id(self._owner_id, draft_id)
        except DraftNotFoundError as error:
            raise _not_found_error() from error
        return _response(record)

    async def update(
        self, draft_id: UUID, request: OutreachDraftUpdateRequest
    ) -> OutreachDraftResponse:
        try:
            record = await self._repository.update(
                owner_id=self._owner_id,
                draft_id=draft_id,
                expected_version=request.expected_version,
                subject=request.subject,
                body=request.body,
            )
        except DraftNotFoundError as error:
            raise _not_found_error() from error
        except DraftVersionConflictError as error:
            raise AppError(
                code="draft_version_conflict",
                message=(
                    "This draft has a newer saved version. Reload it before "
                    "saving again."
                ),
                status_code=409,
            ) from error
        return _response(record)


def _selected_papers(
    mentor: MentorCandidate, selected_ids: list[UUID]
) -> list[MentorSupportingPaper]:
    paper_by_id = {paper.id: paper for paper in mentor.supporting_papers}
    missing = [paper_id for paper_id in selected_ids if paper_id not in paper_by_id]
    if missing:
        raise AppError(
            code="outreach_paper_not_found",
            message="One or more selected papers do not support this researcher.",
            status_code=422,
            details=[
                {
                    "field": "paperIds",
                    "message": "Select only papers shown for the chosen researcher.",
                    "type": "value_error.outreach_paper",
                }
            ],
        )
    return [paper_by_id[paper_id] for paper_id in selected_ids]


def _response(record: OutreachDraft) -> OutreachDraftResponse:
    if record.recipient_author is None:
        raise RuntimeError("A live outreach draft must retain its recipient author.")
    try:
        student_facts = _FACT_LIST_ADAPTER.validate_python(
            record.selected_student_facts
        )
        claim_evidence = _CLAIM_LIST_ADAPTER.validate_python(record.claim_evidence)
    except ValidationError as error:
        raise RuntimeError(
            "Stored outreach evidence does not match its schema."
        ) from error

    selected_papers = [
        OutreachPaperEvidence(
            id=link.paper.id,
            title=link.paper.title,
            publication_year=link.paper.publication_year,
            venue=link.paper.venue,
            evidence_strength=(
                "title-only" if link.paper.abstract is None else "full-abstract"
            ),
            source_url=link.paper.primary_source_url,
            last_verified_at=_as_utc(link.paper.last_verified_at),
        )
        for link in record.paper_links
    ]
    fallback_reason = record.fallback_reason
    return OutreachDraftResponse(
        id=record.id,
        mentor_id=record.recipient_author.id,
        recipient_display_name=record.recipient_display_name,
        recipient_source_url=record.recipient_author.source_url,
        recipient_last_verified_at=_as_utc(record.recipient_author.last_verified_at),
        subject=record.subject,
        body=record.body,
        selected_student_facts=student_facts,
        selected_papers=selected_papers,
        claim_evidence=claim_evidence,
        uncertainty_warnings=record.uncertainty_warnings,
        evidence_map_status=record.evidence_map_status,
        generation=OutreachGenerationMetadata(
            mode=record.generation_mode.value,
            provider=record.provider,
            model=record.model_name,
            prompt_version=record.prompt_version,
            template_version=record.template_version,
            fallback_reason=fallback_reason,
        ),
        draft_version=record.draft_version,
        revisions=[
            OutreachDraftRevisionSummary(
                version=revision.version,
                evidence_map_status=revision.evidence_map_status,
                created_at=_as_utc(revision.created_at),
            )
            for revision in record.revisions
        ],
        created_at=_as_utc(record.created_at),
        updated_at=_as_utc(record.updated_at),
    )


def _not_found_error() -> AppError:
    return AppError(
        code="outreach_draft_not_found",
        message="The requested outreach draft was not found.",
        status_code=404,
    )


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite's naive CURRENT_TIMESTAMP to the public UTC contract."""

    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
