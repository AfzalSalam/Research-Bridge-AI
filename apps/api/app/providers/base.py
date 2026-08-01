from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal, Protocol


class DiscoveryQueryKind(StrEnum):
    TEXT = "text"
    DOI = "doi"
    OPENALEX_ID = "openalex-id"


@dataclass(frozen=True, slots=True)
class ClassifiedDiscoveryQuery:
    """Normalized user input that cannot alter an upstream origin."""

    kind: DiscoveryQueryKind
    value: str
    display_value: str


class ProviderFailureKind(StrEnum):
    AUTHENTICATION = "authentication"
    INVALID_RESPONSE = "invalid-response"
    NETWORK = "network"
    RATE_LIMIT = "rate-limit"
    REJECTED_REQUEST = "rejected-request"
    TEMPORARY = "temporary"


class AcademicProviderError(Exception):
    """A secret-safe provider failure for the discovery service to translate."""

    def __init__(
        self,
        kind: ProviderFailureKind,
        *,
        retryable: bool,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(kind.value)
        self.kind = kind
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class ProviderRateLimit:
    limit: int | None = None
    remaining: int | None = None
    credits_used: int | None = None
    reset_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class RawProviderSearchResult:
    """Validated response envelope with records validated independently later."""

    records: tuple[dict[str, Any], ...]
    total_count: int | None
    retrieved_at: datetime
    rate_limit: ProviderRateLimit
    access_mode: Literal["api-key", "limited-anonymous"]


@dataclass(frozen=True, slots=True)
class NormalizedInstitution:
    openalex_id: str | None
    ror_id: str | None
    display_name: str
    normalized_name: str
    country_code: str | None
    city: str | None
    source_url: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class NormalizedAuthor:
    openalex_id: str | None
    orcid: str | None
    display_name: str
    normalized_name: str
    source_url: str
    is_corresponding: bool | None
    institutions: tuple[NormalizedInstitution, ...]
    content_hash: str


@dataclass(frozen=True, slots=True)
class NormalizedTopic:
    openalex_id: str | None
    display_name: str
    normalized_name: str
    score: float | None


@dataclass(frozen=True, slots=True)
class NormalizedPaper:
    openalex_id: str
    doi: str | None
    title: str
    normalized_title: str
    publication_year: int
    publication_date: date | None
    work_type: str | None
    language: str | None
    is_retracted: bool
    venue: str | None
    abstract: str | None
    evidence_strength: Literal["full-abstract", "title-only"]
    source_url: str
    authors: tuple[NormalizedAuthor, ...]
    topics: tuple[NormalizedTopic, ...]
    content_hash: str


@dataclass(frozen=True, slots=True)
class NormalizedProviderSearchResult:
    papers: tuple[NormalizedPaper, ...]
    total_count: int | None
    skipped_count: int
    invalid_count: int
    excluded_count: int
    warnings: tuple[str, ...]
    retrieved_at: datetime
    rate_limit: ProviderRateLimit
    access_mode: Literal["api-key", "limited-anonymous"]


class AcademicPaperProvider(Protocol):
    """Source adapter used by deterministic paper discovery."""

    name: str

    async def search_papers(
        self, query: ClassifiedDiscoveryQuery, limit: int
    ) -> RawProviderSearchResult: ...
