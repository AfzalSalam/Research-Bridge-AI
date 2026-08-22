from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

from app.db.models.enums import AvailabilityStatus, FundingStatus, WorkMode


@dataclass(frozen=True, slots=True)
class OpportunitySource:
    key: str
    organisation: str


OPPORTUNITY_SOURCES: dict[str, OpportunitySource] = {
    "thealleninstitute": OpportunitySource(
        key="thealleninstitute",
        organisation="Allen Institute for AI (Ai2)",
    ),
    "constructorknowledgelabs": OpportunitySource(
        key="constructorknowledgelabs",
        organisation="Constructor Knowledge Labs",
    ),
    "centerforstrategicandinternationalstudiesinc": OpportunitySource(
        key="centerforstrategicandinternationalstudiesinc",
        organisation="Center for Strategic and International Studies",
    ),
    "verainstituteofjustice": OpportunitySource(
        key="verainstituteofjustice",
        organisation="Vera Institute of Justice",
    ),
}


class OpportunityProviderFailureKind(StrEnum):
    INVALID_RESPONSE = "invalid-response"
    NETWORK = "network"
    RATE_LIMIT = "rate-limit"
    REJECTED_REQUEST = "rejected-request"
    TEMPORARY = "temporary"


class OpportunityProviderError(Exception):
    """Secret-safe failure from one allowlisted board request."""

    def __init__(
        self,
        kind: OpportunityProviderFailureKind,
        *,
        retryable: bool,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(kind.value)
        self.kind = kind
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class RawOpportunityRecord:
    id: int
    title: str
    updated_at: datetime
    location: str
    absolute_url: str
    content: str
    departments: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RawOpportunityBoard:
    source: OpportunitySource
    records: tuple[RawOpportunityRecord, ...]
    invalid_count: int
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class NormalizedOpportunity:
    source_name: str
    source_record_id: str
    source_kind: str
    evidence_confidence: str
    opportunity_type: str
    title: str
    organisation: str
    description: str
    research_fields: tuple[str, ...]
    duration_text: str | None
    eligibility_text: str | None
    country_code: str | None
    location: str | None
    work_mode: WorkMode
    funding: FundingStatus
    availability: AvailabilityStatus
    deadline: date | None
    source_url: str
    application_url: str
    source_updated_at: datetime
    last_verified_at: datetime
    extraction_evidence: tuple[dict[str, str], ...]
    inclusion_signal: str
    search_text: str
    content_hash: str


class OpportunityProvider(Protocol):
    async def fetch_board(self, source: OpportunitySource) -> RawOpportunityBoard: ...
