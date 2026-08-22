from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, HttpUrl, StringConstraints, field_validator

from app.db.models.enums import ApplicationStatus
from app.schemas.base import ApiModel

OpportunityQuery = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)
]


class OpportunitySearchRequest(ApiModel):
    query: OpportunityQuery
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    work_mode: Literal["on-site", "hybrid", "remote", "unclear"] | None = None
    funding: Literal["funded", "unfunded", "unclear"] | None = None
    include_expired: bool = False
    limit: int = Field(default=20, ge=1, le=30)

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized.isalpha():
            raise ValueError("countryCode must contain two letters")
        return normalized


class OpportunityExtractionEvidence(ApiModel):
    field: str
    value: str


class OpportunityResult(ApiModel):
    id: UUID
    source_name: str
    source_kind: Literal["official-ats"]
    source_record_id: str
    evidence_confidence: Literal["high"]
    opportunity_type: Literal[
        "internship", "studentship", "fellowship", "research-assistantship"
    ]
    title: str
    organisation: str
    description_excerpt: str
    research_fields: list[str]
    duration: str | None
    eligibility: str | None
    country_code: str | None
    location: str | None
    work_mode: Literal["on-site", "hybrid", "remote", "unclear"]
    funding: Literal["funded", "unfunded", "unclear"]
    availability: Literal["open", "closed", "unclear"]
    deadline: date | None
    source_url: HttpUrl
    application_url: HttpUrl
    source_updated_at: datetime
    last_verified_at: datetime
    is_stale: bool
    is_expired: bool
    extraction_evidence: list[OpportunityExtractionEvidence]
    inclusion_signal: str
    is_saved: bool
    application_id: UUID | None


class OpportunitySourceStatus(ApiModel):
    key: str
    organisation: str
    status: Literal["success", "error"]
    accepted_count: int = Field(ge=0)
    invalid_count: int = Field(ge=0)
    error_code: str | None = None
    retryable: bool = False


class OpportunitySearchResponse(ApiModel):
    query: str
    results: list[OpportunityResult]
    sources: list[OpportunitySourceStatus]
    partial_failure: bool
    policy_version: str
    retrieved_at: datetime
    ranking_applied: Literal[False] = False


class SavedOpportunity(ApiModel):
    saved_at: datetime
    opportunity: OpportunityResult


class SavedOpportunityListResponse(ApiModel):
    items: list[SavedOpportunity]


class ApplicationCreateRequest(ApiModel):
    opportunity_id: UUID


class ApplicationUpdateRequest(ApiModel):
    status: ApplicationStatus
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
    follow_up_date: date | None
    expected_version: int = Field(ge=1)


class ApplicationEventResponse(ApiModel):
    sequence: int = Field(ge=1)
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    note: str | None
    occurred_at: datetime


class ApplicationResponse(ApiModel):
    id: UUID
    opportunity_id: UUID
    target_label: str
    source_url: HttpUrl
    status: ApplicationStatus
    notes: str
    follow_up_date: date | None
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    events: list[ApplicationEventResponse]
    allowed_next_statuses: list[ApplicationStatus]
    external_submission_performed: Literal[False] = False


class ApplicationListResponse(ApiModel):
    items: list[ApplicationResponse]
