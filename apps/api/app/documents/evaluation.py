"""Offline evaluation of labelled exported retrieval runs; no external calls."""

import math
from statistics import mean

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    relevant: list[str]


class EvaluationRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_id: str
    engine: str = Field(min_length=1)
    retrieved: list[str] = Field(max_length=10)
    citation_valid: list[bool]
    latency_ms: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def aligned(self) -> "EvaluationRun":
        if len(self.retrieved) != len(self.citation_valid):
            raise ValueError("Each retrieved passage needs a citation audit result.")
        return self


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    kind: str = Field(pattern="^(synthetic|labelled-corpus)$")
    passage_ids: list[str] = Field(min_length=1)
    queries: list[EvaluationQuery] = Field(min_length=1)
    runs: list[EvaluationRun] = Field(min_length=1)

    @model_validator(mode="after")
    def references(self) -> "EvaluationDataset":
        ids = set(self.passage_ids)
        queries = {query.id for query in self.queries}
        if len(ids) != len(self.passage_ids) or len(queries) != len(self.queries):
            raise ValueError("Passage and query identifiers must be unique.")
        for query in self.queries:
            if len(set(query.relevant)) != len(query.relevant):
                raise ValueError("Relevance labels must be unique.")
            if not set(query.relevant) <= ids:
                raise ValueError("Relevance label references an unknown passage.")
        seen: set[tuple[str, str]] = set()
        engines: dict[str, set[str]] = {}
        for run in self.runs:
            key = (run.engine, run.query_id)
            if key in seen or run.query_id not in queries:
                raise ValueError("Duplicate run or unknown query.")
            if not set(run.retrieved) <= ids:
                raise ValueError("Retrieved identifier references an unknown passage.")
            seen.add(key)
            engines.setdefault(run.engine, set()).add(run.query_id)
        if any(covered != queries for covered in engines.values()):
            raise ValueError("Every engine must cover every query for comparison.")
        return self


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile, explicitly including zero-latency observations."""
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def evaluate(dataset: EvaluationDataset) -> dict[str, object]:
    labels = {query.id: set(query.relevant) for query in dataset.queries}
    reports: dict[str, object] = {}
    for engine in sorted({run.engine for run in dataset.runs}):
        runs = [run for run in dataset.runs if run.engine == engine]
        recall5, recall10, reciprocal, ndcg = [], [], [], []
        duplicates = total = valid = unsupported = unsupported_returned = 0
        for run in runs:
            relevant = labels[run.query_id]
            seen: set[str] = set()
            gains: list[int] = []
            for passage, citation in zip(
                run.retrieved, run.citation_valid, strict=True
            ):
                duplicate = passage in seen
                duplicates += int(duplicate)
                gains.append(int(passage in relevant and citation and not duplicate))
                seen.add(passage)
                valid += int(citation)
                total += 1
            if not relevant:
                unsupported += 1
                unsupported_returned += int(bool(run.retrieved))
                continue
            recall5.append(sum(gains[:5]) / len(relevant))
            recall10.append(sum(gains[:10]) / len(relevant))
            reciprocal.append(next((1 / (i + 1) for i, g in enumerate(gains) if g), 0))
            dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
            ideal = sum(1 / math.log2(i + 2) for i in range(min(10, len(relevant))))
            ndcg.append(dcg / ideal)
        reports[engine] = {
            "queries": len(runs),
            "answerable_queries": len(recall5),
            "unsupported_queries": unsupported,
            "recall_at_5": mean(recall5) if recall5 else None,
            "recall_at_10": mean(recall10) if recall10 else None,
            "mrr": mean(reciprocal) if reciprocal else None,
            "ndcg_at_10": mean(ndcg) if ndcg else None,
            "duplicate_rate": duplicates / total if total else None,
            "citation_coverage": valid / total if total else None,
            "unsupported_query_retrieval_rate": (
                unsupported_returned / unsupported if unsupported else None
            ),
            "latency_p50_ms": percentile([r.latency_ms for r in runs], 0.5),
            "latency_p95_ms": percentile([r.latency_ms for r in runs], 0.95),
        }
    return {
        "dataset": dataset.name,
        "kind": dataset.kind,
        "engines": reports,
        "notice": "Metrics describe supplied rankings and citation audits only. "
        "Synthetic runs do not measure semantic quality. Retrieved passages are "
        "not generated claims; unsupported-claim rate is not measured.",
    }


def combine_datasets(name: str, datasets: list[EvaluationDataset]) -> EvaluationDataset:
    """Namespace paper-local IDs; require equal engine coverage across papers."""
    if not datasets or len({d.name for d in datasets}) != len(datasets):
        raise ValueError("Provide uniquely named paper datasets.")
    # JSON tuple encoding prevents delimiter collisions in source identifiers.
    import json

    def key(dataset: str, identifier: str) -> str:
        return json.dumps([dataset, identifier], ensure_ascii=True)

    return EvaluationDataset(
        name=name,
        kind="labelled-corpus"
        if all(d.kind == "labelled-corpus" for d in datasets)
        else "synthetic",
        passage_ids=[key(d.name, p) for d in datasets for p in d.passage_ids],
        queries=[
            EvaluationQuery(
                id=key(d.name, q.id), relevant=[key(d.name, p) for p in q.relevant]
            )
            for d in datasets
            for q in d.queries
        ],
        runs=[
            EvaluationRun(
                query_id=key(d.name, r.query_id),
                engine=r.engine,
                retrieved=[key(d.name, p) for p in r.retrieved],
                citation_valid=r.citation_valid,
                latency_ms=r.latency_ms,
            )
            for d in datasets
            for r in d.runs
        ],
    )
