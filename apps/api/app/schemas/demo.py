from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, StringConstraints, field_validator

from app.schemas.base import ApiModel

ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)
]
DiscoveryQuery = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=12, max_length=180)
]


class StudentProfile(ApiModel):
    """Verified student facts allowed to influence a demo draft."""

    id: Literal["demo-student"]
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)
    ]
    program: ShortText
    institution: ShortText
    graduation_year: Annotated[str, StringConstraints(pattern=r"^20\d{2}$")]
    research_interests: Annotated[list[ShortText], Field(min_length=1, max_length=6)]
    skills: Annotated[list[ShortText], Field(min_length=1, max_length=8)]
    project_title: ShortText
    project_summary: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=40, max_length=500)
    ]
    weekly_availability: Literal["5-10 hours", "10-15 hours", "15+ hours"]


class PaperEvidence(ApiModel):
    """Fictional publication evidence with an explicit evidence boundary."""

    id: str
    title: ShortText
    authors: Annotated[list[ShortText], Field(min_length=1)]
    year: int = Field(ge=2000, le=2100)
    venue: ShortText
    summary: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=600)
    ]
    topics: Annotated[list[ShortText], Field(min_length=1)]
    evidence_strength: Literal["full-abstract", "title-only"]
    source_url: HttpUrl


class MentorCandidate(ApiModel):
    """Fictional researcher candidate supported by publication evidence."""

    id: str
    name: ShortText
    role: ShortText
    department: ShortText
    institution: ShortText
    location: ShortText
    research_themes: Annotated[list[ShortText], Field(min_length=1)]
    fit_rationale: Annotated[
        list[
            Annotated[
                str,
                StringConstraints(strip_whitespace=True, min_length=10, max_length=240),
            ]
        ],
        Field(min_length=1),
    ]
    identity_note: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=240)
    ]
    source_url: HttpUrl
    papers: Annotated[list[PaperEvidence], Field(min_length=1)]


class Opportunity(ApiModel):
    """Fictional research opportunity with unknown values kept explicit."""

    id: str
    title: ShortText
    organisation: ShortText
    location: ShortText
    mode: Literal["On-site", "Hybrid", "Remote", "Unknown"]
    funding: Literal["Funded", "Unfunded", "Unknown"]
    availability: Literal["Open", "Closed", "Unknown"]
    deadline: date | None
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=500)
    ]
    topics: Annotated[list[ShortText], Field(min_length=1)]
    source_url: HttpUrl
    last_verified_at: datetime


class DemoBootstrapResponse(ApiModel):
    """Canonical catalog needed to initialize the stateless demo journey."""

    schema_version: Literal[1] = 1
    mode: Literal["fictional-demo"] = "fictional-demo"
    default_query: DiscoveryQuery
    profile: StudentProfile
    mentors: Annotated[list[MentorCandidate], Field(min_length=1)]
    opportunities: Annotated[list[Opportunity], Field(min_length=1)]


class DiscoveryRequest(ApiModel):
    """Bounded input for deterministic demo discovery behavior."""

    query: DiscoveryQuery
    scenario: Literal["complete", "partial", "empty", "error"]


class DiscoveryResponse(ApiModel):
    """Final mock discovery outcome; no score or provider claim is included."""

    status: Literal["complete", "partial", "empty"]
    mentor_ids: list[str]
    source_warning: str | None = None


class OutreachDraftRequest(ApiModel):
    """Evidence selected by a human before draft creation is allowed."""

    profile: StudentProfile
    mentor_id: str
    paper_ids: Annotated[list[str], Field(min_length=1, max_length=2)]

    @field_validator("paper_ids")
    @classmethod
    def require_unique_paper_ids(cls, paper_ids: list[str]) -> list[str]:
        if len(paper_ids) != len(set(paper_ids)):
            raise ValueError("paperIds must not contain duplicates")
        return paper_ids


class ClaimEvidence(ApiModel):
    """Explains which selected records support a draft passage."""

    claim: str
    evidence_ids: Annotated[list[str], Field(min_length=1)]


class OutreachDraft(ApiModel):
    """Editable deterministic draft plus its complete provenance."""

    id: str
    mentor_id: str
    paper_ids: Annotated[list[str], Field(min_length=1, max_length=2)]
    subject: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=160)
    ]
    body: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=80, max_length=5000)
    ]
    selected_student_facts: Annotated[list[str], Field(min_length=1)]
    claim_evidence: Annotated[list[ClaimEvidence], Field(min_length=1)]
    uncertainty_warnings: Annotated[list[str], Field(min_length=1)]
    generated_at: datetime
    updated_at: datetime
    mode: Literal["deterministic-demo"] = "deterministic-demo"
    template_version: Literal["phase-04.v1"] = "phase-04.v1"
    draft_version: Literal[1] = 1
    evidence_links: Annotated[list[HttpUrl], Field(min_length=2)]
