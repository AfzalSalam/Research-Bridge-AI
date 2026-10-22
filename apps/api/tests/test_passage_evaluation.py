import copy
import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.documents.evaluation import EvaluationDataset, evaluate


def fixture():
    return json.loads(
        (
            Path(__file__).parents[1] / "evaluation" / "passage-metric-sanity-v1.json"
        ).read_text(encoding="utf-8")
    )


def test_metrics_penalize_duplicates_and_invalid_citations():
    result = evaluate(EvaluationDataset.model_validate(fixture()))["engines"]["fixture"]
    assert result["recall_at_5"] == 0.5
    assert result["recall_at_10"] == 0.5
    assert result["mrr"] == 0.5
    assert result["ndcg_at_10"] == pytest.approx(
        (1 / math.log2(3)) / (1 + 1 / math.log2(3))
    )
    assert result["duplicate_rate"] == 0.25
    assert result["citation_coverage"] == 0.75
    assert result["unsupported_query_retrieval_rate"] == 0
    assert result["latency_p50_ms"] == 2
    assert result["latency_p95_ms"] == 12


def test_no_retrieval_has_zero_recall_but_unknown_citation_coverage():
    data = fixture()
    for run in data["runs"]:
        run.update(retrieved=[], citation_valid=[])
    result = evaluate(EvaluationDataset.model_validate(data))["engines"]["fixture"]
    assert result["recall_at_10"] == 0
    assert result["citation_coverage"] is None
    assert result["duplicate_rate"] is None


@pytest.mark.parametrize(
    "case",
    [
        "missing_run",
        "duplicate_run",
        "unknown_passage",
        "misaligned",
        "duplicate_label",
        "nonfinite",
    ],
)
def test_invalid_comparisons_are_rejected(case):
    data = fixture()
    if case == "missing_run":
        data["runs"][1]["engine"] = "other"
    elif case == "duplicate_run":
        data["runs"].append(copy.deepcopy(data["runs"][0]))
    elif case == "unknown_passage":
        data["queries"][0]["relevant"] = ["missing"]
    elif case == "misaligned":
        data["runs"][0]["citation_valid"] = []
    elif case == "duplicate_label":
        data["queries"][0]["relevant"] = ["p1", "p1"]
    else:
        data["runs"][0]["latency_ms"] = float("nan")
    with pytest.raises(ValidationError):
        EvaluationDataset.model_validate(data)


def test_unsupported_returns_are_separate_from_answerable_scores():
    data = fixture()
    data["queries"][0]["relevant"] = []
    result = evaluate(EvaluationDataset.model_validate(data))["engines"]["fixture"]
    assert result["answerable_queries"] == 0
    assert result["recall_at_5"] is None
    assert result["mrr"] is None
    assert result["ndcg_at_10"] is None
    assert result["unsupported_query_retrieval_rate"] == 0.5


def test_engines_are_scored_independently_on_identical_query_sets():
    data = fixture()
    better = copy.deepcopy(data["runs"])
    for run in better:
        run["engine"] = "perfect-fixture"
    better[0].update(retrieved=["p1", "p2"], citation_valid=[True, True])
    data["runs"].extend(better)
    result = evaluate(EvaluationDataset.model_validate(data))["engines"]
    assert result["perfect-fixture"]["recall_at_10"] == 1
    assert result["perfect-fixture"]["ndcg_at_10"] == 1
    assert result["fixture"]["recall_at_10"] == 0.5


def test_combination_namespaces_ids_and_preserves_metrics():
    from app.documents.evaluation import combine_datasets

    first = EvaluationDataset.model_validate(fixture())
    second = first.model_copy(update={"name": "second-paper"})
    combined = combine_datasets("two-papers", [first, second])
    assert len(set(combined.passage_ids)) == 6
    result = evaluate(combined)["engines"]["fixture"]
    assert result["queries"] == 4
    assert result["recall_at_10"] == 0.5
    with pytest.raises(ValueError, match="uniquely named"):
        combine_datasets("invalid", [first, first])


def test_combination_rejects_missing_engine_on_one_paper():
    from app.documents.evaluation import combine_datasets

    first = EvaluationDataset.model_validate(fixture())
    data = fixture()
    data["name"] = "second-paper"
    for run in data["runs"]:
        run["engine"] = "different-engine"
    with pytest.raises(ValidationError, match="Every engine"):
        combine_datasets("invalid", [first, EvaluationDataset.model_validate(data)])
