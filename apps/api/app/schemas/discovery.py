from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, HttpUrl, StringConstraints

from app.schemas.base import ApiModel

DiscoveryText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)
]


class PaperDiscoveryRequest(ApiModel):
    """Bounded paper query for the real OpenAlex discovery boundary."""

    query: DiscoveryText
    limit: int = Field(default=12, ge=1, le=25)


class PaperInstitution(ApiModel):
    id: UUID
    openalex_id: str | None
    ror_id: str | None
    display_name: str
    country_code: str | None
    city: str | None
    source_url: HttpUrl


class PaperAuthor(ApiModel):
    id: UUID
    openalex_id: str | None
    orcid: str | None
    display_name: str
    is_corresponding: bool | None
    source_url: HttpUrl
    institutions: list[PaperInstitution]


class PaperTopic(ApiModel):
    id: UUID
    openalex_id: str | None
    display_name: str
    score: float | None = Field(default=None, ge=0, le=1)


class DiscoveredPaper(ApiModel):
    id: UUID
    openalex_id: str
    doi: str | None
    title: str
    publication_year: int = Field(ge=1000, le=2100)
    publication_date: date | None
    work_type: str | None
    language: str | None
    venue: str | None
    abstract_excerpt: str | None
    evidence_strength: Literal["full-abstract", "title-only"]
    source_url: HttpUrl
    last_verified_at: datetime
    authors: list[PaperAuthor]
    topics: list[PaperTopic]


class DiscoverySource(ApiModel):
    name: Literal["OpenAlex"] = "OpenAlex"
    source_url: HttpUrl = HttpUrl("https://openalex.org")
    retrieved_at: datetime
    access_mode: Literal["api-key", "limited-anonymous"]
    cache_status: Literal["hit", "miss"]
    rate_limit_remaining: int | None = Field(default=None, ge=0)
    rate_limit_reset_seconds: int | None = Field(default=None, ge=0)


class PaperDiscoveryResponse(ApiModel):
    status: Literal["complete", "partial", "empty"]
    query: str
    query_kind: Literal["text", "doi", "openalex-id"]
    ordering: Literal["openalex-provider"] = "openalex-provider"
    total_provider_results: int | None = Field(default=None, ge=0)
    returned_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    warnings: list[str]
    source: DiscoverySource
    papers: list[DiscoveredPaper]
