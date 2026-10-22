"""Offline fusion replay; original rankings and labels remain unchanged."""

import json
from pathlib import Path
from time import perf_counter

from app.documents.evaluation import (
    EvaluationDataset,
    EvaluationRun,
    combine_datasets,
    evaluate,
)
from app.documents.hybrid import fuse
from scripts.run_public_paper_pilot import load_source, source_chunks


def main() -> None:
    datasets = []
    for name in ("scikit-learn", "liblinear"):
        root = Path("evaluation")
        manifest = json.loads((root / f"{name}-public-pilot-v1.json").read_text())
        saved = json.loads((root / f"{name}-gemini-pilot-results-v1.json").read_text())
        pages = load_source(Path(f".test-tmp-public-papers/{name}.pdf"), manifest)
        chunks = {f"{c.page}:{c.start}:{c.end}": c for c in source_chunks(pages)}
        original = EvaluationDataset.model_validate(saved["dataset"])
        runs = []
        for query in original.queries:
            inputs = []
            for engine in ("postgresql_fts", "gemini_vector"):
                ranking = next(
                    r
                    for r in original.runs
                    if r.engine == engine and r.query_id == query.id
                )
                inputs.append([chunks[key] for key in ranking.retrieved])
            start = perf_counter()
            selected = fuse(inputs, dict(enumerate(pages, 1)), limit=10)
            runs.append(
                EvaluationRun(
                    query_id=query.id,
                    engine="hybrid_containment_replay",
                    retrieved=[f"{c.page}:{c.start}:{c.end}" for c in selected],
                    citation_valid=[
                        pages[c.page - 1][c.start : c.end] == c.text for c in selected
                    ],
                    latency_ms=(perf_counter() - start) * 1000,
                )
            )
        datasets.append(
            EvaluationDataset(
                name=original.name,
                kind=original.kind,
                passage_ids=original.passage_ids,
                queries=original.queries,
                runs=runs,
            )
        )
    combined = combine_datasets("public-hybrid-containment-replay-v1", datasets)
    result = {
        "dataset": combined.model_dump(),
        "report": evaluate(combined),
        "limitations": (
            "Offline replay of previously observed rankings, not held-out "
            "validation. Timing measures fusion only, not database/network. "
            "No new embeddings or changed relevance labels."
        ),
    }
    Path("evaluation/public-hybrid-containment-replay-v1.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["report"], indent=2))


if __name__ == "__main__":
    main()
