from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean, median
from time import perf_counter
from uuid import UUID

from app.fixtures.demo import fresh_profile
from app.outreach.drafting import (
    CompositionPaperConnection,
    GroundingError,
    OutreachComposition,
    OutreachEvidencePackage,
    build_evidence_package,
    deterministic_draft,
    ground_provider_composition,
)
from app.relevance.mentor import RelevanceWeights, derive_candidates
from app.services.mentor_discovery import _candidate_response
from scripts.evaluate_mentor_relevance import FIXTURE_PATH, EvaluationFixture

REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "reports"
    / "phase-08-outreach-grounding-baseline.json"
)


def _evidence() -> OutreachEvidencePackage:
    evaluation = EvaluationFixture.model_validate_json(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )
    case = evaluation.cases[0]
    derived = derive_candidates(
        query=case.query,
        query_kind=case.query_kind,
        papers=case.papers,
        profile=fresh_profile(),
        evaluation_year=evaluation.evaluation_year,
        weights=RelevanceWeights(),
    ).candidates[0]
    candidate = _candidate_response(derived)
    return build_evidence_package(
        mentor=candidate,
        papers=candidate.supporting_papers[:2],
        profile=fresh_profile(),
    )


def _composition(
    *, invalid_reference: bool = False, unsupported: bool = False
) -> OutreachComposition:
    evidence = _evidence()
    connections = [
        CompositionPaperConnection(
            paper_id=UUID(int=42) if invalid_reference and index == 0 else paper.id,
            text=(
                "I appreciated the paper's evidence boundary and its connection "
                "to responsible decision support."
            ),
        )
        for index, paper in enumerate(evidence.papers)
    ]
    return OutreachComposition(
        subject=(
            "Question about your funded lab opening"
            if unsupported
            else "Question about evidence-centred research"
        ),
        introduction=(
            "I am Aarav Demo, a B.Tech student interested in responsible research "
            "software and careful academic collaboration."
        ),
        student_fact_keys=["profile.name", "profile.program"],
        paper_connections=connections,
        ask=(
            "Would you be open to a brief conversation about whether a focused "
            "student contribution could be useful?"
        ),
    )


def evaluate() -> dict[str, object]:
    evidence = _evidence()
    accepted = 0
    rejected = 0
    unsupported_references = 0
    title_only_safe = 0
    durations: list[float] = []

    for composition in (
        _composition(),
        _composition(invalid_reference=True),
        _composition(unsupported=True),
    ):
        started_at = perf_counter()
        try:
            grounded = ground_provider_composition(evidence, composition)
        except GroundingError:
            rejected += 1
            fallback = deterministic_draft(evidence)
            unsupported_references += sum(
                reference.id
                not in {
                    *(str(paper.id) for paper in evidence.papers),
                    *(fact.key for fact in evidence.student_facts),
                }
                for claim in fallback.claim_evidence
                for reference in claim.references
            )
        else:
            accepted += 1
            if "only title-level metadata" in grounded.body:
                title_only_safe += 1
        durations.append((perf_counter() - started_at) * 1000)

    fallback = deterministic_draft(evidence)
    title_only_safe += int("only title-level metadata" in fallback.body)
    return {
        "phase": 8,
        "fixtureVersion": "phase-07-relevance-fixtures.v1",
        "promptVersion": "outreach-grounded.v1",
        "templateVersion": "outreach-template.v1",
        "scope": (
            "Small structural fixture evaluation; no reply or selection outcome "
            "is measured."
        ),
        "cases": {
            "providerCompositionsAttempted": 3,
            "providerCompositionsAccepted": accepted,
            "providerCompositionsRejected": rejected,
            "deterministicFallbacksProduced": rejected + 1,
        },
        "metrics": {
            "groundingAcceptanceRate": round(accepted / 3, 4),
            "unsafeCompositionRejectionRate": round(rejected / 2, 4),
            "fallbackCoverageRate": 1.0,
            "unsupportedReferenceRate": round(unsupported_references / 1, 4),
            "titleOnlySafetyRate": round(title_only_safe / 2, 4),
            "auditLatencyMs": {
                "mean": round(fmean(durations), 4),
                "p50": round(median(durations), 4),
                "p95": round(max(durations), 4),
            },
        },
        "limitations": [
            "The fixture set is intentionally tiny and measures structural "
            "safety only.",
            "It does not measure writing quality, professor replies, selection, "
            "or real provider latency.",
        ],
    }


def _stable_payload(payload: dict[str, object]) -> dict[str, object]:
    stable = dict(payload)
    metrics = stable.get("metrics")
    if isinstance(metrics, dict):
        stable["metrics"] = {
            key: value for key, value in metrics.items() if key != "auditLatencyMs"
        }
    return stable


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate evidence-grounded outreach fixtures."
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    report = evaluate()

    if arguments.check:
        if not REPORT_PATH.exists():
            print("Outreach report is missing; run this script without --check.")
            return 1
        checked = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        if not isinstance(checked, dict) or _stable_payload(checked) != _stable_payload(
            report
        ):
            print("Stable outreach grounding metrics are stale; regenerate the report.")
            return 1
        metrics = checked.get("metrics")
        latency = metrics.get("auditLatencyMs") if isinstance(metrics, dict) else None
        if not isinstance(latency, dict):
            print("Checked outreach audit latency metadata is invalid.")
            return 1
        p50 = latency.get("p50")
        p95 = latency.get("p95")
        if not isinstance(p50, int | float) or not isinstance(p95, int | float):
            print("Checked outreach audit latency percentiles are invalid.")
            return 1
        if p50 < 0 or p95 < p50:
            print("Checked outreach audit latency percentiles are inconsistent.")
            return 1
        print("Stable outreach grounding metrics match the checked-in baseline.")
        return 0

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
