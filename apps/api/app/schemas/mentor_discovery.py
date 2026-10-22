from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, HttpUrl, StringConstraints

from app.relevance.mentor import (
    EvidenceConfidence,
    PolicyFeature,
    RelevanceBand,
)
from app.schemas.base import ApiModel
from app.schemas.discovery import (
    DiscoverySource,
    DiscoveryText,
    PaperInstitution,
    PaperTopic,
)

ExplanationText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=10, max_length=260)
]


class MentorDiscoveryRequest(ApiModel):
    """Bounded request for paper-backed candidate derivation."""

    query: DiscoveryText
    paper_limit: int = Field(default=20, ge=1, le=30)
    candidate_limit: int = Field(default=12, ge=1, le=20)


class PolicyWeight(ApiModel):
    feature: PolicyFeature
    label: str
    weight: float = Field(ge=0, le=1)


class RelevancePolicy(ApiModel):
    version: Literal["placement-relevance-v1"]
    ordering: Literal["deterministic-evidence-policy"] = "deterministic-evidence-policy"
    weights: list[PolicyWeight]
    score_visibility: Literal["bands-and-contributions-only"] = (
        "bands-and-contributions-only"
    )


class ProfileRelevanceInputs(ApiModel):
    """Non-private profile labels returned so the user can audit matching."""

    research_interests: list[str]
    skills: list[str]
    project_title: str


class MentorFeatureContribution(ApiModel):
    feature: PolicyFeature
    label: str
    value: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=1)
    explanation: ExplanationText
    matched_terms: list[str]
    evidence_paper_ids: list[UUID]


class MentorAuthorship(ApiModel):
    position: int = Field(ge=1)
    is_corresponding: bool | None
    affiliations_at_publication: list[PaperInstitution]


class MentorSupportingPaper(ApiModel):
    id: UUID
    openalex_id: str
    doi: str | None
    title: str
    publication_year: int
    publication_date: date | None
    work_type: str | None
    language: str | None
    venue: str | None
    abstract_excerpt: str | None
    evidence_strength: Literal["full-abstract", "title-only"]
    source_url: HttpUrl
    last_verified_at: datetime
    authorship: MentorAuthorship
    topics: list[PaperTopic]


class MentorCandidate(ApiModel):
    """Candidate facts and evidence, with unsupported employment fields absent."""

    id: UUID
    display_name: str
    openalex_id: str | None
    orcid: str | None
    source_url: HttpUrl
    last_verified_at: datetime
    academic_title: None = None
    current_institution: None = None
    availability: Literal["unknown"] = "unknown"
    research_themes: list[str]
    supporting_paper_count: int = Field(ge=1)
    supporting_papers: list[MentorSupportingPaper]
    relevance_band: RelevanceBand
    evidence_confidence: EvidenceConfidence
    evidence_completeness: float = Field(ge=0, le=1)
    contributions: list[MentorFeatureContribution]
    warnings: list[str]


class MentorDerivationQuality(ApiModel):
    author_appearances: int = Field(ge=0)
    unique_candidates: int = Field(ge=0)
    duplicate_collapse_rate: float = Field(ge=0, le=1)
    mean_evidence_coverage: float = Field(ge=0, le=1)
    unsupported_claim_rate: float = Field(ge=0, le=1)


class MentorDiscoveryTiming(ApiModel):
    retrieval_and_persistence_ms: int = Field(ge=0)
    heuristic_ms: int = Field(ge=0)
    total_ms: int = Field(ge=0)


class MentorDiscoveryResponse(ApiModel):
    status: Literal["complete", "partial", "empty"]
    query: str
    query_kind: Literal["text", "doi", "openalex-id"]
    ordering: Literal["deterministic-evidence-policy"] = "deterministic-evidence-policy"
    profile_mode: Literal["authenticated-account"] = "authenticated-account"
    profile_inputs: ProfileRelevanceInputs
    policy: RelevancePolicy
    source: DiscoverySource
    paper_count: int = Field(ge=0)
    author_appearance_count: int = Field(ge=0)
    derived_candidate_count: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    warnings: list[str]
    quality: MentorDerivationQuality
    timing: MentorDiscoveryTiming
    candidates: list[MentorCandidate]
