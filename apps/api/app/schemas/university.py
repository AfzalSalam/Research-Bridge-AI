from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import ApiModel
from app.schemas.discovery import DiscoveryText

UniversityId = Literal["oist", "kaust", "ista", "iitgn", "iitk", "iisc", "epfl"]
WorkMode = Literal["remote", "on-site", "hybrid", "not-specified"]


class UniversityScanRequest(ApiModel):
    query: DiscoveryText
    target: Literal[10, 20, 30] = 20
    region: Literal["both", "india", "international"] = "both"
    universities: list[UniversityId] | None = Field(
        default=None, min_length=1, max_length=7
    )

    @field_validator("universities")
    @classmethod
    def unique_sources(
        cls, value: list[UniversityId] | None
    ) -> list[UniversityId] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("Choose each university only once")
        return value


class WebsitePaper(ApiModel):
    id: str
    university: str
    title: str | None
    citation: str
    doi: str | None
    publication_url: str
    source_url: str
    checked_at: datetime
    matched_terms: list[str]


class UniversityProgram(ApiModel):
    university: str
    name: str
    source_url: str
    checked_at: datetime
    status: Literal["rolling", "open", "closed", "not-confirmed"]
    deadline: str | None
    status_evidence: str | None
    work_mode: WorkMode
    work_mode_evidence: str | None
    eligibility_evidence: str | None
    application_note: str


class UniversitySourceSummary(ApiModel):
    name: str
    website: str
    registry_url: str | None = None


class UniversityScanSnapshot(ApiModel):
    state: Literal["scanning", "complete", "partial", "empty", "error"]
    query: str
    target: int
    papers: list[WebsitePaper] = Field(default_factory=list)
    programs: list[UniversityProgram] = Field(default_factory=list)
    pages_attempted: int = 0
    pages_read: int = 0
    elapsed_seconds: int = 0
    budget_seconds: int = 120
    current_university: str | None = None
    stop_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    sources: list[UniversitySourceSummary] = Field(default_factory=list)
