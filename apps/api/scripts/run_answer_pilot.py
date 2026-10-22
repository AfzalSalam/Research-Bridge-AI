"""Opt-in evaluation of frozen public papers; never accepts private documents."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.core.config import Settings
from app.documents.answer_prompts import (
    ANSWER_PROMPT_VERSION,
    CONTEXT_PROMPT_VERSION,
    REVIEW_PROMPT_VERSION,
)
from app.documents.answers import AnswerProviderError, answer, evidence_bundle
from app.documents.citation_choices import CHOICE_PROMPT_VERSION
from app.documents.contracts import PdfPage
from app.documents.gemini_answers import ANSWER_MODEL, GeminiAnswerProvider
from app.documents.hybrid import fuse
from scripts.run_public_paper_pilot import load_source, source_chunks


class ObservedProvider:
    """Record only allowlisted error codes, never exception payloads."""

    def __init__(self, provider):
        self.provider = provider
        self.calls = []

    async def invoke(self, stage, system, payload):
        start = perf_counter()
        record = {"stage": stage, "outcome": "started"}
        self.calls.append(record)
        try:
            result = await getattr(self.provider, stage)(system, payload)
            record["outcome"] = "validated"
            return result
        except AnswerProviderError as exc:
            allowed = {
                "answer_provider_unavailable",
                "answer_provider_refused",
                "invalid_answer_envelope",
                "invalid_answer_choices",
                "answer_input_too_large",
                "answer_response_too_large",
                "unexpected_answer_model",
            }
            record["outcome"] = str(exc) if str(exc) in allowed else "provider_error"
            raise
        finally:
            record["latency_ms"] = round((perf_counter() - start) * 1000, 2)

    async def generate(self, system, payload):
        return await self.invoke("generate", system, payload)

    async def review(self, system, payload):
        return await self.invoke("review", system, payload)


def cases():
    result = []
    for name in ("scikit-learn", "liblinear"):
        root = Path("evaluation")
        manifest = json.loads((root / f"{name}-public-pilot-v1.json").read_text())
        saved = json.loads((root / f"{name}-gemini-pilot-results-v1.json").read_text())
        pages = load_source(Path(f".test-tmp-public-papers/{name}.pdf"), manifest)
        chunks = {f"{c.page}:{c.start}:{c.end}": c for c in source_chunks(pages)}
        for query in manifest["queries"]:
            rankings = []
            for engine in ("postgresql_fts", "gemini_vector"):
                ranking = next(
                    r
                    for r in saved["dataset"]["runs"]
                    if r["engine"] == engine and r["query_id"] == query["id"]
                )
                rankings.append([chunks[key] for key in ranking["retrieved"]])
            selected = fuse(rankings, dict(enumerate(pages, 1)), limit=5)
            evidence = evidence_bundle(
                [PdfPage(number=i, text=text) for i, text in enumerate(pages, 1)],
                selected,
            )
            result.append(
                (
                    {
                        "id": f"{name}:{query['id']}",
                        "question": query["question"],
                        "expected_answerable": bool(query["evidence"]),
                        "source_url": manifest["source_url"],
                        "pdf_sha256": manifest["pdf_sha256"],
                        "evidence": [e.model_dump() for e in evidence],
                    },
                    evidence,
                )
            )
    if len(result) != 12:
        raise ValueError("Frozen pilot must contain exactly 12 cases")
    return result


async def run(output: Path):
    if output.exists():
        raise ValueError("Output already exists; preserve previous measurements")
    inputs = cases()  # Verify all source hashes before any provider call.
    report = {
        "model": ANSWER_MODEL,
        "started_at": datetime.now(UTC).isoformat(),
        "answer_prompt": ANSWER_PROMPT_VERSION,
        "citation_choice_prompt": CHOICE_PROMPT_VERSION,
        "review_prompt": REVIEW_PROMPT_VERSION,
        "context_prompt": CONTEXT_PROMPT_VERSION,
        "complete": False,
        "cases": [],
        "limitations": (
            "Two public papers; provisional labels; observed retrieval corpus; "
            "not held-out accuracy. Model review is not independent human verification."
        ),
    }

    def save():
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    provider = GeminiAnswerProvider(Settings())
    try:
        save()
        for case, evidence in inputs:
            start = perf_counter()
            observed = ObservedProvider(provider)
            result = await answer(case["question"], evidence, observed)
            case.update(
                result=result.model_dump(),
                provider_calls=observed.calls,
                latency_ms=round((perf_counter() - start) * 1000, 2),
            )
            report["cases"].append(case)
            save()
            print(case["id"], result.status, result.reason, flush=True)
            if result.reason == "provider_unavailable":
                break  # Stop service failures; score invalid answers as failures.
            if len(report["cases"]) < len(inputs):
                await asyncio.sleep(6)
        report["complete"] = len(report["cases"]) == len(inputs)
        report["finished_at"] = datetime.now(UTC).isoformat()
        save()
    finally:
        await provider.aclose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-public-text-to-gemini", action="store_true", required=True
    )
    parser.add_argument(
        "--output", type=Path, default=Path("evaluation/public-answer-pilot-v1.json")
    )
    args = parser.parse_args()
    asyncio.run(run(args.output))


if __name__ == "__main__":
    main()
