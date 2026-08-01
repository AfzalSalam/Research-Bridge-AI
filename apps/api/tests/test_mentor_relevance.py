import pytest

from app.fixtures.demo import fresh_profile
from app.relevance.mentor import RelevanceWeights, derive_candidates, tokenize
from scripts.evaluate_mentor_relevance import FIXTURE_PATH, EvaluationFixture, evaluate


def fixture() -> EvaluationFixture:
    return EvaluationFixture.model_validate_json(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )


def test_unicode_tokenization_is_normalized_and_removes_policy_stopwords() -> None:
    assert tokenize("  Human-centred AI, AND clinical AI  ") == {
        "human",
        "centred",
        "ai",
        "clinical",
    }


def test_candidate_order_and_contributions_are_deterministic() -> None:
    evaluation = fixture()
    case = evaluation.cases[0]
    arguments = {
        "query": case.query,
        "query_kind": case.query_kind,
        "papers": case.papers,
        "profile": fresh_profile(),
        "evaluation_year": evaluation.evaluation_year,
        "weights": RelevanceWeights(),
    }

    first = derive_candidates(**arguments)
    second = derive_candidates(**arguments)

    assert first == second
    assert first.quality.author_appearances == 3
    assert first.quality.unique_candidates == 2
    assert first.candidates[0].display_name == "Mira Sen"
    assert len(first.candidates[0].supporting_papers) == 2
    assert first.quality.unsupported_claim_rate == 0
    assert all(
        contribution.evidence_paper_ids
        for candidate in first.candidates
        for contribution in candidate.contributions
        if contribution.value > 0
    )


def test_distinct_author_ids_are_not_merged_by_matching_names() -> None:
    evaluation = fixture()
    paper = evaluation.cases[0].papers[0].model_copy(deep=True)
    paper.authors[1].display_name = paper.authors[0].display_name

    result = derive_candidates(
        query=evaluation.cases[0].query,
        query_kind="text",
        papers=[paper],
        profile=fresh_profile(),
        evaluation_year=evaluation.evaluation_year,
        weights=RelevanceWeights(),
    )

    assert len(result.candidates) == 2
    assert len({candidate.id for candidate in result.candidates}) == 2


def test_recency_boundary_and_fixture_quality_metrics_are_explicit() -> None:
    evaluation = fixture()
    case = evaluation.cases[1]
    result = derive_candidates(
        query=case.query,
        query_kind=case.query_kind,
        papers=case.papers,
        profile=fresh_profile(),
        evaluation_year=evaluation.evaluation_year,
        weights=RelevanceWeights(),
    )
    recency = next(
        item
        for item in result.candidates[0].contributions
        if item.feature == "recent-activity"
    )
    metrics = evaluate()["fixtureMetrics"]

    assert recency.value == 0.5
    assert isinstance(metrics, dict)
    assert metrics["duplicateCollapseRate"] == 0.25
    assert metrics["unsupportedClaimRate"] == 0


def test_domain_policy_rejects_invalid_weight_totals() -> None:
    with pytest.raises(ValueError, match="must total one"):
        RelevanceWeights(query_evidence=0.5)
