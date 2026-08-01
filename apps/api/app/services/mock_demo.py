from collections.abc import Callable
from datetime import UTC, datetime

from app.core.errors import AppError
from app.fixtures.demo import (
    DEMO_DISCOVERY_QUERY,
    fresh_mentors,
    fresh_opportunities,
    fresh_profile,
)
from app.schemas.demo import (
    ClaimEvidence,
    DemoBootstrapResponse,
    DiscoveryRequest,
    DiscoveryResponse,
    MentorCandidate,
    OutreachDraft,
    OutreachDraftRequest,
    PaperEvidence,
    StudentProfile,
)


class MockDemoService:
    """Stateless, deterministic implementation used by the recruiter demo."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    async def bootstrap(self) -> DemoBootstrapResponse:
        return DemoBootstrapResponse(
            default_query=DEMO_DISCOVERY_QUERY,
            profile=fresh_profile(),
            mentors=fresh_mentors(),
            opportunities=fresh_opportunities(),
        )

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResponse:
        mentors = fresh_mentors()
        if request.scenario == "error":
            raise AppError(
                code="demo_source_unavailable",
                message=(
                    "The fictional OpenAlex adapter timed out. "
                    "No cached result was substituted."
                ),
                status_code=503,
            )
        if request.scenario == "empty":
            return DiscoveryResponse(status="empty", mentor_ids=[])
        if request.scenario == "partial":
            return DiscoveryResponse(
                status="partial",
                mentor_ids=[mentor.id for mentor in mentors[:2]],
                source_warning=(
                    "One fictional source did not respond; two evidence-linked "
                    "candidates remain reviewable."
                ),
            )
        return DiscoveryResponse(
            status="complete",
            mentor_ids=[mentor.id for mentor in mentors],
        )

    async def create_outreach_draft(
        self, request: OutreachDraftRequest
    ) -> OutreachDraft:
        mentor = self._find_mentor(request.mentor_id)
        paper_by_id = {paper.id: paper for paper in mentor.papers}
        missing_ids = [
            paper_id for paper_id in request.paper_ids if paper_id not in paper_by_id
        ]
        if missing_ids:
            raise AppError(
                code="paper_evidence_not_found",
                message="One or more selected papers do not belong to this mentor.",
                status_code=422,
                details=[
                    {
                        "field": "paperIds",
                        "message": "Unknown paper IDs: " + ", ".join(missing_ids),
                        "type": "value_error.paper_evidence",
                    }
                ],
            )

        papers = [paper_by_id[paper_id] for paper_id in request.paper_ids]
        generated_at = self._clock()
        return self._build_draft(mentor, papers, request.profile, generated_at)

    @staticmethod
    def _find_mentor(mentor_id: str) -> MentorCandidate:
        mentor = next(
            (candidate for candidate in fresh_mentors() if candidate.id == mentor_id),
            None,
        )
        if mentor is None:
            raise AppError(
                code="mentor_not_found",
                message="The selected fictional mentor does not exist.",
                status_code=404,
            )
        return mentor

    @staticmethod
    def _paper_connection(paper: PaperEvidence, profile: StudentProfile) -> str:
        if paper.evidence_strength == "title-only":
            return (
                f"I found the title of your {paper.year} paper, “{paper.title},” "
                f"relevant to my interest in {paper.topics[0]}. Because only "
                "title-level metadata is available in this demo, I would be "
                "interested in learning more about the work."
            )
        topics = " and ".join(paper.topics[:2])
        return (
            f"I was particularly interested in your {paper.year} paper, "
            f"“{paper.title}.” "
            f"Its focus on {topics} connects with the way I have been thinking "
            f"about {profile.research_interests[0]}."
        )

    @classmethod
    def _build_draft(
        cls,
        mentor: MentorCandidate,
        papers: list[PaperEvidence],
        profile: StudentProfile,
        generated_at: datetime,
    ) -> OutreachDraft:
        paper_paragraphs = "\n\n".join(
            cls._paper_connection(paper, profile) for paper in papers
        )
        lowered_summary = (
            profile.project_summary[0].lower() + profile.project_summary[1:]
        )
        body = (
            f"Dear {mentor.name.replace(' (fictional)', '')},\n\n"
            f"I am {profile.name}, a {profile.program} at {profile.institution}. "
            f"My interests include {', '.join(profile.research_interests)}.\n\n"
            f"{paper_paragraphs}\n\n"
            f"For my project, “{profile.project_title},” I {lowered_summary} "
            f"I can currently commit {profile.weekly_availability} each week.\n\n"
            "If this direction is relevant to your current work, I would value the "
            "opportunity to ask a few focused questions about possible student "
            "research contributions. I understand that availability and funding "
            "have not been verified.\n\n"
            f"Thank you for your time,\n{profile.name}"
        )
        warnings = [
            "Mentor availability, funding, and contact details are unknown.",
            "Review and edit every sentence before using this draft.",
        ]
        if any(paper.evidence_strength == "title-only" for paper in papers):
            warnings.append(
                "Title-only evidence is referenced cautiously and supports no "
                "technical claim."
            )
        return OutreachDraft(
            id=f"draft-{mentor.id}",
            mentor_id=mentor.id,
            paper_ids=[paper.id for paper in papers],
            subject=f"Prospective student interested in {mentor.research_themes[0]}",
            body=body,
            selected_student_facts=[
                "profile.name",
                "profile.program",
                "profile.institution",
                "profile.researchInterests",
                "profile.projectTitle",
                "profile.projectSummary",
                "profile.weeklyAvailability",
            ],
            claim_evidence=[
                ClaimEvidence(
                    claim=f"Reference to {paper.title}", evidence_ids=[paper.id]
                )
                for paper in papers
            ],
            uncertainty_warnings=warnings,
            generated_at=generated_at,
            updated_at=generated_at,
            evidence_links=[mentor.source_url, *[paper.source_url for paper in papers]],
        )
