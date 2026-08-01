from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.demo import StudentProfile
from app.schemas.mentor_discovery import MentorCandidate, MentorSupportingPaper
from app.schemas.outreach import (
    ClaimEvidenceReference,
    DraftClaimEvidence,
    SelectedStudentFact,
    StudentFactKey,
)

PROMPT_VERSION = "outreach-grounded.v1"
TEMPLATE_VERSION = "outreach-template.v1"

FallbackReason = Literal[
    "deterministic-requested",
    "provider-not-configured",
    "provider-unavailable",
    "provider-refused",
    "invalid-provider-output",
    "grounding-check-failed",
]
ProviderFailureReason = Literal[
    "provider-unavailable", "provider-refused", "invalid-provider-output"
]

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_UNSUPPORTED_ASSERTIONS = re.compile(
    r"\b(?:you are accepting|you have an opening|your funded|your funding|"
    r"your lab at|your group at|you are a professor|you are professor|"
    r"guaranteed|acceptance probability|response rate)\b",
    flags=re.IGNORECASE,
)


class CompositionPaperConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: UUID
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=900)
    ]


class OutreachComposition(BaseModel):
    """Strict provider output; final greeting, signoff, and maps are deterministic."""

    model_config = ConfigDict(extra="forbid")

    subject: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=160)
    ]
    introduction: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=900)
    ]
    student_fact_keys: Annotated[list[StudentFactKey], Field(min_length=1)]
    paper_connections: Annotated[
        list[CompositionPaperConnection], Field(min_length=1, max_length=2)
    ]
    ask: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=700)
    ]

    @field_validator("student_fact_keys")
    @classmethod
    def require_unique_fact_keys(
        cls, values: list[StudentFactKey]
    ) -> list[StudentFactKey]:
        if len(values) != len(set(values)):
            raise ValueError("student fact keys must be unique")
        return values


@dataclass(frozen=True, slots=True)
class OutreachEvidencePackage:
    mentor: MentorCandidate
    papers: tuple[MentorSupportingPaper, ...]
    profile: StudentProfile
    student_facts: tuple[SelectedStudentFact, ...]


@dataclass(frozen=True, slots=True)
class GroundedDraft:
    subject: str
    body: str
    selected_student_facts: tuple[SelectedStudentFact, ...]
    claim_evidence: tuple[DraftClaimEvidence, ...]
    uncertainty_warnings: tuple[str, ...]


class DraftProviderError(Exception):
    def __init__(self, reason: ProviderFailureReason) -> None:
        super().__init__(reason)
        self.reason = reason


class GroundingError(Exception):
    """A structurally valid composition still exceeds the evidence boundary."""


class OutreachDraftGenerator(Protocol):
    name: str
    model: str

    async def generate(
        self, evidence: OutreachEvidencePackage
    ) -> OutreachComposition: ...


def build_evidence_package(
    *,
    mentor: MentorCandidate,
    papers: list[MentorSupportingPaper],
    profile: StudentProfile,
) -> OutreachEvidencePackage:
    facts = (
        SelectedStudentFact(key="profile.name", label="Name", value=profile.name),
        SelectedStudentFact(
            key="profile.program", label="Degree program", value=profile.program
        ),
        SelectedStudentFact(
            key="profile.institution",
            label="Institution",
            value=profile.institution,
        ),
        SelectedStudentFact(
            key="profile.researchInterests",
            label="Research interests",
            value=", ".join(profile.research_interests),
        ),
        SelectedStudentFact(
            key="profile.skills", label="Skills", value=", ".join(profile.skills)
        ),
        SelectedStudentFact(
            key="profile.projectTitle",
            label="Project title",
            value=profile.project_title,
        ),
        SelectedStudentFact(
            key="profile.projectSummary",
            label="Project summary",
            value=profile.project_summary,
        ),
        SelectedStudentFact(
            key="profile.weeklyAvailability",
            label="Weekly availability",
            value=profile.weekly_availability,
        ),
    )
    return OutreachEvidencePackage(
        mentor=mentor,
        papers=tuple(papers),
        profile=profile,
        student_facts=facts,
    )


def deterministic_draft(evidence: OutreachEvidencePackage) -> GroundedDraft:
    profile = evidence.profile
    used_keys: tuple[StudentFactKey, ...] = (
        "profile.name",
        "profile.program",
        "profile.institution",
        "profile.researchInterests",
        "profile.projectTitle",
        "profile.projectSummary",
        "profile.weeklyAvailability",
    )
    introduction = (
        f"I am {profile.name}, a {profile.program} student at "
        f"{profile.institution}. My research interests include "
        f"{', '.join(profile.research_interests)}."
    )
    connections = [
        _deterministic_paper_connection(paper, profile) for paper in evidence.papers
    ]
    lowered_summary = profile.project_summary[0].lower() + profile.project_summary[1:]
    project = (
        f"In my project, “{profile.project_title},” {lowered_summary} "
        "I can currently commit "
        f"{profile.weekly_availability} each week."
    )
    ask = (
        "If this direction is relevant to your current work, would you be open to "
        "a brief conversation about where a student contribution could be useful? "
        "I understand that availability and funding have not been verified."
    )
    body = _assemble_body(
        recipient=evidence.mentor.display_name,
        student_name=profile.name,
        introduction=introduction,
        connections=[*connections, project],
        ask=ask,
    )
    selected_facts = _facts_for_keys(evidence.student_facts, used_keys)
    claims = [
        DraftClaimEvidence(
            claim=introduction,
            references=[_student_reference(fact) for fact in selected_facts[:4]],
        ),
        *[
            DraftClaimEvidence(
                claim=connection,
                references=[_paper_reference(paper)],
            )
            for paper, connection in zip(evidence.papers, connections, strict=True)
        ],
        DraftClaimEvidence(
            claim=project,
            references=[
                _student_reference(fact)
                for fact in selected_facts
                if fact.key
                in {
                    "profile.projectTitle",
                    "profile.projectSummary",
                    "profile.weeklyAvailability",
                }
            ],
        ),
    ]
    return GroundedDraft(
        subject=_deterministic_subject(evidence),
        body=body,
        selected_student_facts=selected_facts,
        claim_evidence=tuple(claims),
        uncertainty_warnings=_warnings(evidence),
    )


def ground_provider_composition(
    evidence: OutreachEvidencePackage, composition: OutreachComposition
) -> GroundedDraft:
    expected_ids = [paper.id for paper in evidence.papers]
    actual_ids = [connection.paper_id for connection in composition.paper_connections]
    if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(expected_ids):
        raise GroundingError("provider paper references do not match the selection")

    allowed_keys = {fact.key for fact in evidence.student_facts}
    if not set(composition.student_fact_keys) <= allowed_keys:
        raise GroundingError("provider used a student fact outside the allowlist")

    connection_by_id = {
        connection.paper_id: connection.text
        for connection in composition.paper_connections
    }
    connections = [
        (
            _deterministic_paper_connection(paper, evidence.profile)
            if paper.evidence_strength == "title-only"
            else connection_by_id[paper.id]
        )
        for paper in evidence.papers
    ]
    # Title-only provider prose is discarded before semantic safety checks. It
    # never reaches the draft and therefore cannot turn a title into a finding.
    prose = [
        composition.subject,
        composition.introduction,
        composition.ask,
        *connections,
    ]
    if any(_CONTROL_CHARACTERS.search(value) for value in prose):
        raise GroundingError("provider output contains invalid control characters")
    if any(_UNSUPPORTED_ASSERTIONS.search(value) for value in prose):
        raise GroundingError("provider asserted an explicitly unknown fact")
    selected_facts = _facts_for_keys(
        evidence.student_facts, tuple(composition.student_fact_keys)
    )
    body = _assemble_body(
        recipient=evidence.mentor.display_name,
        student_name=evidence.profile.name,
        introduction=composition.introduction,
        connections=connections,
        ask=composition.ask,
    )
    claims = [
        DraftClaimEvidence(
            claim=composition.introduction,
            references=[_student_reference(fact) for fact in selected_facts],
        ),
        *[
            DraftClaimEvidence(
                claim=connection,
                references=[_paper_reference(paper)],
            )
            for paper, connection in zip(evidence.papers, connections, strict=True)
        ],
    ]
    return GroundedDraft(
        subject=composition.subject,
        body=body,
        selected_student_facts=selected_facts,
        claim_evidence=tuple(claims),
        uncertainty_warnings=_warnings(evidence),
    )


def _deterministic_subject(evidence: OutreachEvidencePackage) -> str:
    theme = next(
        (
            value
            for value in (
                *evidence.mentor.research_themes,
                *evidence.profile.research_interests,
            )
            if value.strip()
        ),
        "your research",
    )
    return f"Prospective student interested in {theme}"[:160]


def _deterministic_paper_connection(
    paper: MentorSupportingPaper, profile: StudentProfile
) -> str:
    title = f"your {paper.publication_year} paper, “{paper.title}”"
    if paper.evidence_strength == "title-only":
        topic = paper.topics[0].display_name if paper.topics else "this topic"
        return (
            f"I found the title of {title} relevant to my interest in {topic}. "
            "Because only title-level metadata is available, I would value the "
            "opportunity to learn more without assuming its methods or findings."
        )
    interest = profile.research_interests[0]
    topics = " and ".join(topic.display_name for topic in paper.topics[:2])
    connection = (
        f"I was particularly interested in {title}. Its verified abstract"
        f"{' and listed focus on ' + topics if topics else ''} connects with my "
        f"interest in {interest}, and I would like to understand the work more deeply."
    )
    return connection


def _assemble_body(
    *,
    recipient: str,
    student_name: str,
    introduction: str,
    connections: list[str],
    ask: str,
) -> str:
    sections = [
        f"Dear {recipient},",
        introduction,
        *connections,
        ask,
        f"Thank you for your time,\n{student_name}",
    ]
    return "\n\n".join(section.strip() for section in sections)


def _facts_for_keys(
    facts: tuple[SelectedStudentFact, ...], keys: tuple[StudentFactKey, ...]
) -> tuple[SelectedStudentFact, ...]:
    by_key = {fact.key: fact for fact in facts}
    return tuple(by_key[key] for key in keys)


def _student_reference(fact: SelectedStudentFact) -> ClaimEvidenceReference:
    return ClaimEvidenceReference(
        type="student-fact", id=fact.key, label=fact.label, source_url=None
    )


def _paper_reference(paper: MentorSupportingPaper) -> ClaimEvidenceReference:
    return ClaimEvidenceReference(
        type="paper", id=str(paper.id), label=paper.title, source_url=paper.source_url
    )


def _warnings(evidence: OutreachEvidencePackage) -> tuple[str, ...]:
    warnings = [
        "Recipient academic title, current institution, contact details, "
        "availability, and funding are unknown.",
        "Verify the recipient and every edited sentence against official "
        "sources before use.",
        "This draft is prepared for human review and cannot be sent by "
        "Research Bridge AI.",
    ]
    if any(paper.evidence_strength == "title-only" for paper in evidence.papers):
        warnings.append(
            "At least one selected paper has title-only evidence; no method or "
            "result claim is made for it."
        )
    return tuple(warnings)
