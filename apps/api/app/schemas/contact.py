from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import ApiModel


class ContactLookupRequest(ApiModel):
    profile_url: str | None = Field(default=None, max_length=1800)
    refresh: bool = False


class PublicEmail(ApiModel):
    email: str
    source_url: str
    identity_evidence: list[str]
    evidence_urls: list[str]
    extraction: Literal["mailto", "text", "obfuscated"]
    checked_at: datetime


class ContactProfile(ApiModel):
    source_url: str
    reason: str


class ContactLookupResponse(ApiModel):
    author_id: UUID
    author_name: str
    status: Literal["found", "not-found", "needs-review", "unsupported", "blocked"]
    emails: list[PublicEmail] = Field(default_factory=list)
    profiles: list[ContactProfile] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime
    pages_checked: int = 0
    elapsed_seconds: int = 0
    cache_hit: bool = False
    lookup_url: str | None = None
    institution_sources: list[str] = Field(default_factory=list)
    verification: Literal["official-profile-evidence-not-deliverability"] = (
        "official-profile-evidence-not-deliverability"
    )
