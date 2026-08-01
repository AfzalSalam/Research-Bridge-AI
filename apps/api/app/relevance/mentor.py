from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from statistics import fmean
from typing import Literal
from uuid import UUID

from app.schemas.demo import StudentProfile
from app.schemas.discovery import DiscoveredPaper, PaperAuthor

type PolicyFeature = Literal[
    "query-evidence",
    "profile-alignment",
    "supporting-depth",
    "recent-activity",
    "evidence-completeness",
]
type RelevanceBand = Literal["strong", "promising", "exploratory"]
type EvidenceConfidence = Literal["high", "moderate", "limited"]

POLICY_VERSION = "placement-relevance-v1"
_TOKEN_PATTERN = re.compile(r"[^\W_]+", flags=re.UNICODE)
_TOP_PAPER_WEIGHTS = (0.6, 0.3, 0.1)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "using",
        "with",
    }
)


@dataclass(frozen=True, slots=True)
class RelevanceWeights:
    """Auditable weights for candidate ordering; values must total one."""

    query_evidence: float = 0.35
    profile_alignment: float = 0.25
    supporting_depth: float = 0.15
    recent_activity: float = 0.15
    evidence_completeness: float = 0.10

    def __post_init__(self) -> None:
        values = self.as_dict().values()
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("Relevance weights must be between zero and one.")
        if abs(sum(values) - 1) > 1e-9:
            raise ValueError("Relevance weights must total one.")

    def as_dict(self) -> dict[PolicyFeature, float]:
        return {
            "query-evidence": self.query_evidence,
            "profile-alignment": self.profile_alignment,
            "supporting-depth": self.supporting_depth,
            "recent-activity": self.recent_activity,
            "evidence-completeness": self.evidence_completeness,
        }


@dataclass(frozen=True, slots=True)
class SupportingPaper:
    paper: DiscoveredPaper
    authorship: PaperAuthor


@dataclass(frozen=True, slots=True)
class FeatureContribution:
    feature: PolicyFeature
    value: float
    weight: float
    contribution: float
    matched_terms: tuple[str, ...]
    evidence_paper_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class DerivedCandidate:
    id: UUID
    display_name: str
    openalex_id: str | None
    orcid: str | None
    source_url: str
    supporting_papers: tuple[SupportingPaper, ...]
    research_themes: tuple[str, ...]
    relevance_band: RelevanceBand
    evidence_confidence: EvidenceConfidence
    evidence_completeness: float
    contributions: tuple[FeatureContribution, ...]
    warnings: tuple[str, ...]
    internal_total: float


@dataclass(frozen=True, slots=True)
class DerivationQuality:
    author_appearances: int
    unique_candidates: int
    duplicate_collapse_rate: float
    mean_evidence_coverage: float
    unsupported_claim_rate: float


@dataclass(frozen=True, slots=True)
class CandidateDerivation:
    candidates: tuple[DerivedCandidate, ...]
    quality: DerivationQuality


@dataclass(frozen=True, slots=True)
class _PaperOverlap:
    value: float
    matched_terms: frozenset[str]


def tokenize(value: str | None) -> frozenset[str]:
    """Normalize human text into stable lexical terms without language guessing."""

    if not value:
        return frozenset()
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return frozenset(
        token
        for token in _TOKEN_PATTERN.findall(normalized)
        if len(token) > 1 and token not in _STOPWORDS
    )


def derive_candidates(
    *,
    query: str,
    query_kind: Literal["text", "doi", "openalex-id"],
    papers: list[DiscoveredPaper],
    profile: StudentProfile,
    evaluation_year: int,
    weights: RelevanceWeights,
) -> CandidateDerivation:
    """Group paper authors and order them using evidence-only policy features."""

    grouped: dict[UUID, list[SupportingPaper]] = defaultdict(list)
    seen_pairs: set[tuple[UUID, UUID]] = set()
    author_appearances = 0
    for paper in papers:
        for author in paper.authors:
            author_appearances += 1
            pair = (author.id, paper.id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            grouped[author.id].append(SupportingPaper(paper=paper, authorship=author))

    candidates = [
        _derive_candidate(
            query=query,
            query_kind=query_kind,
            supporting=tuple(supporting),
            profile=profile,
            evaluation_year=evaluation_year,
            weights=weights,
        )
        for supporting in grouped.values()
    ]
    candidates.sort(
        key=lambda item: (
            -item.internal_total,
            -len(item.supporting_papers),
            unicodedata.normalize("NFKC", item.display_name).casefold(),
            str(item.id),
        )
    )

    factual_claims = [
        contribution
        for candidate in candidates
        for contribution in candidate.contributions
        if contribution.value > 0
    ]
    unsupported_claims = sum(
        not contribution.evidence_paper_ids for contribution in factual_claims
    )
    unique_candidates = len(candidates)
    collapsed = max(author_appearances - unique_candidates, 0)
    return CandidateDerivation(
        candidates=tuple(candidates),
        quality=DerivationQuality(
            author_appearances=author_appearances,
            unique_candidates=unique_candidates,
            duplicate_collapse_rate=_rounded(
                collapsed / author_appearances if author_appearances else 0
            ),
            mean_evidence_coverage=_rounded(
                fmean(candidate.evidence_completeness for candidate in candidates)
                if candidates
                else 0
            ),
            unsupported_claim_rate=_rounded(
                unsupported_claims / len(factual_claims) if factual_claims else 0
            ),
        ),
    )


def _derive_candidate(
    *,
    query: str,
    query_kind: Literal["text", "doi", "openalex-id"],
    supporting: tuple[SupportingPaper, ...],
    profile: StudentProfile,
    evaluation_year: int,
    weights: RelevanceWeights,
) -> DerivedCandidate:
    author = supporting[0].authorship
    papers = tuple(item.paper for item in supporting)
    query_value, query_terms, query_papers = _query_evidence(
        query=query, query_kind=query_kind, papers=papers
    )
    profile_value, profile_terms = _profile_alignment(profile, papers)
    depth_value = min(len(papers), 3) / 3
    recency_value = _recent_activity(papers, evaluation_year)
    completeness_value = fmean(_paper_completeness(item) for item in supporting)
    all_ids = tuple(paper.id for paper in papers)

    feature_values: tuple[
        tuple[PolicyFeature, float, tuple[str, ...], tuple[UUID, ...]], ...
    ] = (
        ("query-evidence", query_value, query_terms, query_papers),
        ("profile-alignment", profile_value, profile_terms, all_ids),
        ("supporting-depth", depth_value, (), all_ids),
        ("recent-activity", recency_value, (), all_ids),
        ("evidence-completeness", completeness_value, (), all_ids),
    )
    weight_map = weights.as_dict()
    contributions = tuple(
        FeatureContribution(
            feature=feature,
            value=_rounded(value),
            weight=weight_map[feature],
            contribution=_rounded(value * weight_map[feature]),
            matched_terms=matched_terms,
            evidence_paper_ids=evidence_ids,
        )
        for feature, value, matched_terms, evidence_ids in feature_values
    )
    internal_total = sum(item.contribution for item in contributions)
    warnings = [
        "Current institution, academic title, availability, and contact details "
        "are unknown."
    ]
    if any(paper.abstract_excerpt is None for paper in papers):
        warnings.append(
            "One or more supporting papers provide title-level evidence only."
        )
    if any(paper.publication_year > evaluation_year for paper in papers):
        warnings.append(
            "A supporting publication year is in the future and needs metadata "
            "verification."
        )

    return DerivedCandidate(
        id=author.id,
        display_name=author.display_name,
        openalex_id=author.openalex_id,
        orcid=author.orcid,
        source_url=str(author.source_url),
        supporting_papers=supporting,
        research_themes=_research_themes(papers),
        relevance_band=_relevance_band(internal_total),
        evidence_confidence=_evidence_confidence(
            author=author,
            paper_count=len(papers),
            completeness=completeness_value,
        ),
        evidence_completeness=_rounded(completeness_value),
        contributions=contributions,
        warnings=tuple(warnings),
        internal_total=_rounded(internal_total),
    )


def _query_evidence(
    *,
    query: str,
    query_kind: Literal["text", "doi", "openalex-id"],
    papers: tuple[DiscoveredPaper, ...],
) -> tuple[float, tuple[str, ...], tuple[UUID, ...]]:
    if query_kind != "text":
        normalized = query.casefold()
        matching = tuple(
            paper.id
            for paper in papers
            if (query_kind == "doi" and (paper.doi or "").casefold() == normalized)
            or (
                query_kind == "openalex-id"
                and paper.openalex_id.casefold() == normalized
            )
        )
        return (1.0 if matching else 0.0, (query,) if matching else (), matching)

    query_tokens = tokenize(query)
    overlaps = [
        (_paper_query_overlap(query_tokens, paper), paper.id) for paper in papers
    ]
    overlaps.sort(key=lambda item: (-item[0].value, str(item[1])))
    selected = [item for item in overlaps if item[0].value > 0][
        : len(_TOP_PAPER_WEIGHTS)
    ]
    available_weight = sum(_TOP_PAPER_WEIGHTS[: len(selected)])
    value = (
        sum(
            overlap.value * _TOP_PAPER_WEIGHTS[index]
            for index, (overlap, _) in enumerate(selected)
        )
        / available_weight
        if available_weight
        else 0
    )
    matched_terms = tuple(
        sorted({term for overlap, _ in selected for term in overlap.matched_terms})
    )
    evidence_ids = tuple(
        paper_id for overlap, paper_id in selected if overlap.value > 0
    )
    return value, matched_terms, evidence_ids


def _paper_query_overlap(
    query_tokens: frozenset[str], paper: DiscoveredPaper
) -> _PaperOverlap:
    if not query_tokens:
        return _PaperOverlap(value=0, matched_terms=frozenset())
    topic_tokens = frozenset().union(
        *(tokenize(topic.display_name) for topic in paper.topics)
    )
    title_tokens = tokenize(paper.title)
    abstract_tokens = tokenize(paper.abstract_excerpt)
    matched = query_tokens & (topic_tokens | title_tokens | abstract_tokens)
    value = (
        0.5 * _coverage(query_tokens, topic_tokens)
        + 0.3 * _coverage(query_tokens, title_tokens)
        + 0.2 * _coverage(query_tokens, abstract_tokens)
    )
    return _PaperOverlap(value=value, matched_terms=matched)


def _profile_alignment(
    profile: StudentProfile, papers: tuple[DiscoveredPaper, ...]
) -> tuple[float, tuple[str, ...]]:
    evidence_tokens: frozenset[str] = frozenset().union(
        *(_paper_evidence_tokens(paper) for paper in papers)
    )
    interest_tokens = tokenize(" ".join(profile.research_interests))
    skill_tokens = tokenize(" ".join(profile.skills))
    project_tokens = tokenize(f"{profile.project_title} {profile.project_summary}")
    matched = (interest_tokens | skill_tokens | project_tokens) & evidence_tokens
    value = (
        0.5 * _coverage(interest_tokens, evidence_tokens)
        + 0.2 * _coverage(skill_tokens, evidence_tokens)
        + 0.3 * _coverage(project_tokens, evidence_tokens)
    )
    return value, tuple(sorted(matched))


def _paper_evidence_tokens(paper: DiscoveredPaper) -> frozenset[str]:
    topic_tokens: frozenset[str] = frozenset().union(
        *(tokenize(topic.display_name) for topic in paper.topics)
    )
    return tokenize(paper.title) | tokenize(paper.abstract_excerpt) | topic_tokens


def _recent_activity(papers: tuple[DiscoveredPaper, ...], year: int) -> float:
    age = max(year - max(paper.publication_year for paper in papers), 0)
    if age <= 2:
        return 1
    if age <= 5:
        return 0.75
    if age <= 8:
        return 0.5
    if age <= 12:
        return 0.25
    return 0


def _paper_completeness(item: SupportingPaper) -> float:
    paper = item.paper
    author = item.authorship
    return (
        (0.30 if paper.abstract_excerpt else 0)
        + (0.15 if paper.doi else 0)
        + (0.15 if paper.venue else 0)
        + (0.15 if paper.topics else 0)
        + (0.15 if author.openalex_id or author.orcid else 0)
        + (0.10 if author.institutions else 0)
    )


def _research_themes(papers: tuple[DiscoveredPaper, ...]) -> tuple[str, ...]:
    topics: dict[str, tuple[str, float]] = {}
    for paper in papers:
        for topic in paper.topics:
            key = unicodedata.normalize("NFKC", topic.display_name).casefold()
            score = topic.score or 0
            previous = topics.get(key)
            if previous is None or score > previous[1]:
                topics[key] = (topic.display_name, score)
    ordered = sorted(topics.values(), key=lambda item: (-item[1], item[0].casefold()))
    return tuple(name for name, _ in ordered[:5])


def _coverage(needles: frozenset[str], haystack: frozenset[str]) -> float:
    return len(needles & haystack) / len(needles) if needles else 0


def _evidence_confidence(
    *, author: PaperAuthor, paper_count: int, completeness: float
) -> EvidenceConfidence:
    stable_identity = author.openalex_id is not None or author.orcid is not None
    if stable_identity and paper_count >= 2 and completeness >= 0.75:
        return "high"
    if stable_identity and completeness >= 0.5:
        return "moderate"
    return "limited"


def _relevance_band(value: float) -> RelevanceBand:
    if value >= 0.70:
        return "strong"
    if value >= 0.45:
        return "promising"
    return "exploratory"


def _rounded(value: float) -> float:
    return round(value, 4)
