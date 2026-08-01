from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Protocol

from app.relevance.mentor import (
    POLICY_VERSION,
    CandidateDerivation,
    DerivedCandidate,
    FeatureContribution,
    PolicyFeature,
    RelevanceWeights,
    derive_candidates,
)
from app.schemas.discovery import PaperDiscoveryRequest
from app.schemas.mentor_discovery import (
    MentorAuthorship,
    MentorCandidate,
    MentorDerivationQuality,
    MentorDiscoveryRequest,
    MentorDiscoveryResponse,
    MentorDiscoveryTiming,
    MentorFeatureContribution,
    MentorSupportingPaper,
    PolicyWeight,
    ProfileRelevanceInputs,
    RelevancePolicy,
)
from app.services.discovery import PaperDiscoveryReader
from app.services.profile import ProfileReader

_FEATURE_LABELS: dict[PolicyFeature, str] = {
    "query-evidence": "Query evidence",
    "profile-alignment": "Profile alignment",
    "supporting-depth": "Supporting depth",
    "recent-activity": "Recent activity",
    "evidence-completeness": "Evidence completeness",
}


class MentorDiscoveryReader(Protocol):
    async def search(
        self, request: MentorDiscoveryRequest
    ) -> MentorDiscoveryResponse: ...


class MentorDiscoveryService:
    """Compose paper retrieval, profile facts, and a pure ordering policy."""

    def __init__(
        self,
        *,
        papers: PaperDiscoveryReader,
        profiles: ProfileReader,
        weights: RelevanceWeights,
        evaluation_year: int,
        timer: Callable[[], float] = perf_counter,
    ) -> None:
        self._papers = papers
        self._profiles = profiles
        self._weights = weights
        self._evaluation_year = evaluation_year
        self._timer = timer

    async def search(self, request: MentorDiscoveryRequest) -> MentorDiscoveryResponse:
        started_at = self._timer()
        profile = await self._profiles.get_profile()
        retrieval_started_at = self._timer()
        paper_response = await self._papers.search(
            PaperDiscoveryRequest(query=request.query, limit=request.paper_limit)
        )
        retrieval_finished_at = self._timer()
        derivation = derive_candidates(
            query=paper_response.query,
            query_kind=paper_response.query_kind,
            papers=paper_response.papers,
            profile=profile,
            evaluation_year=self._evaluation_year,
            weights=self._weights,
        )
        heuristic_finished_at = self._timer()
        candidates = derivation.candidates[: request.candidate_limit]
        finished_at = self._timer()

        status = paper_response.status
        if not candidates:
            status = "empty"
        return MentorDiscoveryResponse(
            status=status,
            query=paper_response.query,
            query_kind=paper_response.query_kind,
            profile_inputs=ProfileRelevanceInputs(
                research_interests=profile.research_interests,
                skills=profile.skills,
                project_title=profile.project_title,
            ),
            policy=_policy(self._weights),
            source=paper_response.source,
            paper_count=len(paper_response.papers),
            author_appearance_count=derivation.quality.author_appearances,
            derived_candidate_count=derivation.quality.unique_candidates,
            returned_count=len(candidates),
            warnings=paper_response.warnings,
            quality=_quality(derivation),
            timing=MentorDiscoveryTiming(
                retrieval_and_persistence_ms=_milliseconds(
                    retrieval_started_at, retrieval_finished_at
                ),
                heuristic_ms=_milliseconds(
                    retrieval_finished_at, heuristic_finished_at
                ),
                total_ms=_milliseconds(started_at, finished_at),
            ),
            candidates=[_candidate_response(candidate) for candidate in candidates],
        )


def _policy(weights: RelevanceWeights) -> RelevancePolicy:
    return RelevancePolicy(
        version=POLICY_VERSION,
        weights=[
            PolicyWeight(
                feature=feature,
                label=_FEATURE_LABELS[feature],
                weight=weight,
            )
            for feature, weight in weights.as_dict().items()
        ],
    )


def _quality(derivation: CandidateDerivation) -> MentorDerivationQuality:
    quality = derivation.quality
    return MentorDerivationQuality(
        author_appearances=quality.author_appearances,
        unique_candidates=quality.unique_candidates,
        duplicate_collapse_rate=quality.duplicate_collapse_rate,
        mean_evidence_coverage=quality.mean_evidence_coverage,
        unsupported_claim_rate=quality.unsupported_claim_rate,
    )


def _candidate_response(candidate: DerivedCandidate) -> MentorCandidate:
    return MentorCandidate(
        id=candidate.id,
        display_name=candidate.display_name,
        openalex_id=candidate.openalex_id,
        orcid=candidate.orcid,
        source_url=candidate.source_url,
        last_verified_at=max(
            item.paper.last_verified_at for item in candidate.supporting_papers
        ),
        research_themes=list(candidate.research_themes),
        supporting_paper_count=len(candidate.supporting_papers),
        supporting_papers=[
            MentorSupportingPaper(
                id=item.paper.id,
                openalex_id=item.paper.openalex_id,
                doi=item.paper.doi,
                title=item.paper.title,
                publication_year=item.paper.publication_year,
                publication_date=item.paper.publication_date,
                work_type=item.paper.work_type,
                language=item.paper.language,
                venue=item.paper.venue,
                abstract_excerpt=item.paper.abstract_excerpt,
                evidence_strength=item.paper.evidence_strength,
                source_url=item.paper.source_url,
                last_verified_at=item.paper.last_verified_at,
                authorship=MentorAuthorship(
                    position=next(
                        index
                        for index, author in enumerate(item.paper.authors, start=1)
                        if author.id == candidate.id
                    ),
                    is_corresponding=item.authorship.is_corresponding,
                    affiliations_at_publication=item.authorship.institutions,
                ),
                topics=item.paper.topics,
            )
            for item in candidate.supporting_papers
        ],
        relevance_band=candidate.relevance_band,
        evidence_confidence=candidate.evidence_confidence,
        evidence_completeness=candidate.evidence_completeness,
        contributions=[
            _contribution_response(item) for item in candidate.contributions
        ],
        warnings=list(candidate.warnings),
    )


def _contribution_response(
    contribution: FeatureContribution,
) -> MentorFeatureContribution:
    explanations: dict[PolicyFeature, str] = {
        "query-evidence": (
            "Measures lexical overlap between the query and verified paper titles, "
            "topics, and available abstracts."
        ),
        "profile-alignment": (
            "Compares saved interests, skills, and the project summary with the "
            "candidate's supporting publications."
        ),
        "supporting-depth": (
            "Rewards up to three distinct supporting publications for this author."
        ),
        "recent-activity": (
            "Uses only the newest supporting publication year, not inferred career "
            "status or availability."
        ),
        "evidence-completeness": (
            "Checks which identifiers, abstract, venue, topics, and publication-time "
            "affiliations are present."
        ),
    }
    return MentorFeatureContribution(
        feature=contribution.feature,
        label=_FEATURE_LABELS[contribution.feature],
        value=contribution.value,
        weight=contribution.weight,
        contribution=contribution.contribution,
        explanation=explanations[contribution.feature],
        matched_terms=list(contribution.matched_terms),
        evidence_paper_ids=list(contribution.evidence_paper_ids),
    )


def _milliseconds(started_at: float, finished_at: float) -> int:
    return max(round((finished_at - started_at) * 1000), 0)
