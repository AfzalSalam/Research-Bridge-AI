from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, HttpUrl, StringConstraints, field_validator

from app.schemas.base import ApiModel
from app.schemas.discovery import DiscoveryText

DraftSubject = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=5, max_length=160)
]
DraftBody = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=80, max_length=5000)
]
StudentFactKey = Literal[
    "profile.name",
    "profile.program",
    "profile.institution",
    "profile.researchInterests",
    "profile.skills",
    "profile.projectTitle",
    "profile.projectSummary",
    "profile.weeklyAvailability",
]


class OutreachDraftCreateRequest(ApiModel):
    """Human-selected IDs; factual evidence is always resolved on the server."""

    query: DiscoveryText
    mentor_id: UUID
    paper_ids: Annotated[list[UUID], Field(min_length=1, max_length=2)]
    generation_preference: Literal["auto", "deterministic"] = "auto"

    @field_validator("paper_ids")
    @classmethod
    def require_unique_papers(cls, values: list[UUID]) -> list[UUID]:
        if len(values) != len(set(values)):
            raise ValueError("paperIds must not contain duplicates")
        return values


class OutreachDraftUpdateRequest(ApiModel):
    subject: DraftSubject
    body: DraftBody
    expected_version: int = Field(ge=1)


class SelectedStudentFact(ApiModel):
    key: StudentFactKey
    label: str
    value: str


class OutreachPaperEvidence(ApiModel):
    id: UUID
    title: str
    publication_year: int
    venue: str | None
    evidence_strength: Literal["full-abstract", "title-only"]
    source_url: HttpUrl
    last_verified_at: datetime


class ClaimEvidenceReference(ApiModel):
    type: Literal["student-fact", "paper"]
    id: str
    label: str
    source_url: HttpUrl | None = None


class DraftClaimEvidence(ApiModel):
    claim: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1200)
    ]
    references: Annotated[list[ClaimEvidenceReference], Field(min_length=1)]


class OutreachGenerationMetadata(ApiModel):
    mode: Literal["deterministic", "llm"]
    provider: str | None
    model: str | None
    prompt_version: str | None
    template_version: str
    fallback_reason: (
        Literal[
            "deterministic-requested",
            "provider-not-configured",
            "provider-unavailable",
            "provider-refused",
            "invalid-provider-output",
            "grounding-check-failed",
        ]
        | None
    )


class OutreachDraftRevisionSummary(ApiModel):
    version: int = Field(ge=1)
    evidence_map_status: Literal["verified-generated", "manual-edit-needs-review"]
    created_at: datetime


class OutreachDraftResponse(ApiModel):
    """Latest editable draft snapshot with complete evidence metadata."""

    id: UUID
    mentor_id: UUID
    recipient_display_name: str
    recipient_contact: str | None = None
    contact_provenance: dict[str, str] | None = None
    recipient_source_url: HttpUrl
    recipient_last_verified_at: datetime
    subject: DraftSubject
    body: DraftBody
    selected_student_facts: Annotated[list[SelectedStudentFact], Field(min_length=1)]
    selected_papers: Annotated[
        list[OutreachPaperEvidence], Field(min_length=1, max_length=2)
    ]
    claim_evidence: Annotated[list[DraftClaimEvidence], Field(min_length=1)]
    uncertainty_warnings: Annotated[list[str], Field(min_length=1)]
    evidence_map_status: Literal["verified-generated", "manual-edit-needs-review"]
    generation: OutreachGenerationMetadata
    draft_version: int = Field(ge=1)
    revisions: Annotated[list[OutreachDraftRevisionSummary], Field(min_length=1)]
    created_at: datetime
    updated_at: datetime
    can_send: Literal[False] = False
