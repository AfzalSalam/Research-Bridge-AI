from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.fixtures.demo import fresh_profile
from app.relevance.mentor import POLICY_VERSION, RelevanceWeights, derive_candidates
from app.schemas.discovery import DiscoveredPaper

API_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = API_ROOT / "evaluation" / "mentor-relevance-v1.json"
REPORT_PATH = API_ROOT / "reports" / "phase-07-relevance-baseline.json"
REPETITIONS = 100


class EvaluationCase(BaseModel):
    model_config = ConfigDict(alias_generator=None, populate_by_name=True)

    query: str
    query_kind: Literal["text", "doi", "openalex-id"] = Field(alias="queryKind")
    papers: list[DiscoveredPaper]


class EvaluationFixture(BaseModel):
    model_config = ConfigDict(alias_generator=None, populate_by_name=True)

    fixture_version: str = Field(alias="fixtureVersion")
    evaluation_year: int = Field(alias="evaluationYear")
    cases: list[EvaluationCase]


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(math.ceil(percentile * len(ordered)) - 1, 0)
    return round(ordered[index], 4)


def evaluate() -> dict[str, object]:
    """Evaluate only deterministic fixture behavior and pure-policy latency."""

    fixture = EvaluationFixture.model_validate_json(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )
    profile = fresh_profile()
    weights = RelevanceWeights()
    first_pass = [
        derive_candidates(
            query=case.query,
            query_kind=case.query_kind,
            papers=case.papers,
            profile=profile,
            evaluation_year=fixture.evaluation_year,
            weights=weights,
        )
        for case in fixture.cases
    ]

    latencies: list[float] = []
    for _ in range(REPETITIONS):
        for case in fixture.cases:
            started_at = perf_counter()
            derive_candidates(
                query=case.query,
                query_kind=case.query_kind,
                papers=case.papers,
                profile=profile,
                evaluation_year=fixture.evaluation_year,
                weights=weights,
            )
            latencies.append((perf_counter() - started_at) * 1000)

    appearances = sum(item.quality.author_appearances for item in first_pass)
    candidates = [candidate for item in first_pass for candidate in item.candidates]
    unsupported = sum(
        not contribution.evidence_paper_ids
        for candidate in candidates
        for contribution in candidate.contributions
        if contribution.value > 0
    )
    factual_contributions = sum(
        contribution.value > 0
        for candidate in candidates
        for contribution in candidate.contributions
    )
    return {
        "policyVersion": POLICY_VERSION,
        "fixtureVersion": fixture.fixture_version,
        "evaluationYear": fixture.evaluation_year,
        "scope": "Deterministic local fixtures; not a real-world ranking benchmark.",
        "fixtureMetrics": {
            "queryCases": len(fixture.cases),
            "casesWithCandidates": sum(bool(item.candidates) for item in first_pass),
            "candidateRetrievalSuccessRate": round(
                sum(bool(item.candidates) for item in first_pass) / len(first_pass), 4
            ),
            "authorAppearances": appearances,
            "uniqueCandidates": len(candidates),
            "duplicateCollapseRate": round(
                (appearances - len(candidates)) / appearances if appearances else 0,
                4,
            ),
            "meanEvidenceCoverage": round(
                fmean(item.evidence_completeness for item in candidates)
                if candidates
                else 0,
                4,
            ),
            "unsupportedClaimRate": round(
                unsupported / factual_contributions if factual_contributions else 0,
                4,
            ),
        },
        "purePolicyLatencyMs": {
            "samples": len(latencies),
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "note": "Local process timing excludes provider, database, and HTTP time.",
        },
        "limitations": [
            "The fixture is intentionally tiny and cannot support Recall, MRR, "
            "or nDCG.",
            "Lexical overlap does not prove semantic or supervisory suitability.",
            "Professor title, current institution, contact, and availability are "
            "not evaluated.",
        ],
    }


def _stable_payload(payload: dict[str, object]) -> dict[str, object]:
    stable = dict(payload)
    stable.pop("purePolicyLatencyMs", None)
    return stable


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate mentor relevance fixtures.")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    payload = evaluate()

    if arguments.check:
        if not REPORT_PATH.exists():
            print("Relevance report is missing; run this script without --check.")
            return 1
        checked = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        if not isinstance(checked, dict) or _stable_payload(checked) != _stable_payload(
            payload
        ):
            print("Stable relevance metrics are stale; regenerate the report.")
            return 1
        latency = checked.get("purePolicyLatencyMs")
        if not isinstance(latency, dict):
            print("Checked relevance latency metadata is invalid.")
            return 1
        p50 = latency.get("p50")
        p95 = latency.get("p95")
        if not isinstance(p50, int | float) or not isinstance(p95, int | float):
            print("Checked relevance latency percentiles are invalid.")
            return 1
        if p50 < 0 or p95 < p50:
            print("Checked relevance latency percentiles are inconsistent.")
            return 1
        print("Stable relevance metrics match the checked-in baseline.")
        return 0

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Exported {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
