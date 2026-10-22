"""Explicit opt-in live Gemini evaluation of repository-frozen public papers only."""

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.core.config import Settings
from app.documents.embeddings import EmbeddingBatch, EmbeddingError
from app.documents.gemini import GeminiEmbeddings
from app.documents.providers import GEMINI
from app.documents.vectors import valid_batch
from scripts.run_public_paper_pilot import (
    SemanticInputs,
    load_source,
    run,
    source_chunks,
)

ROOT = Path(__file__).resolve().parents[1]
PILOTS = {
    "scikit-learn": "scikit-learn-public-pilot-v1.json",
    "liblinear": "liblinear-public-pilot-v1.json",
}
MAX_REQUESTS = 100
MAX_INPUT_BYTES = 200_000


def preflight(pdf: Path, manifest: dict) -> tuple[list[str], list[dict]]:
    chunks = source_chunks(load_source(pdf, manifest))
    queries = manifest["queries"]
    texts = [chunk.text for chunk in chunks]
    if not texts or not queries or len(texts) + len(queries) > MAX_REQUESTS:
        raise ValueError("Public pilot exceeds request budget.")
    if len({q["id"] for q in queries}) != len(queries):
        raise ValueError("Duplicate query identifiers.")
    if any(not q["question"].strip() or len(q["question"]) > 500 for q in queries):
        raise ValueError("Invalid benchmark question.")
    size = sum(len((GEMINI.document_prefix + t).encode()) for t in texts)
    size += sum(len((GEMINI.query_prefix + q["question"]).encode()) for q in queries)
    if size * 3 > MAX_INPUT_BYTES:
        raise ValueError("Public pilot exceeds conservative input byte budget.")
    return texts, queries


async def prepare(pdf: Path, manifest: dict, settings: Settings) -> SemanticInputs:
    texts, queries = preflight(pdf, manifest)
    documents = GeminiEmbeddings(settings)
    questions = GeminiEmbeddings(settings, query=True)
    vectors = []
    latency = {}
    embedded = {}
    start = perf_counter()
    try:
        for value in texts:
            result = await documents.embed([value])
            if result.model != GEMINI.model or not valid_batch(result, 1):
                raise EmbeddingError("invalid_embedding_response")
            vectors.extend(result.vectors)
            await asyncio.sleep(2)  # Pace requests; errors abort, no wrapper retries.
        indexing_ms = (perf_counter() - start) * 1000
        for query in queries:
            start = perf_counter()
            result = await questions.embed([query["question"]])
            latency[query["id"]] = (perf_counter() - start) * 1000
            if result.model != GEMINI.model or not valid_batch(result, 1):
                raise EmbeddingError("invalid_embedding_response")
            embedded[query["id"]] = result
            await asyncio.sleep(2)
    finally:
        await documents.aclose()
        await questions.aclose()
    return SemanticInputs(
        EmbeddingBatch(GEMINI.model, 1536, tuple(vectors), 0),
        embedded,
        latency,
        indexing_ms,
    )


async def evaluate_pilot(name: str, pdf: Path, output: Path, url: str) -> dict:
    if not url.startswith("postgresql+asyncpg://"):
        raise ValueError("Use a migrated disposable PostgreSQL database.")
    manifest = json.loads(
        (ROOT / "evaluation" / PILOTS[name]).read_text(encoding="utf-8")
    )
    semantic = await prepare(pdf, manifest, Settings())
    result = await run(pdf, manifest, url, semantic)
    result["evaluated_at"] = datetime.now(UTC).isoformat()
    result["source_manifest"] = PILOTS[name]
    result["pdf_sha256"] = manifest["pdf_sha256"]
    result["request_budget"] = MAX_REQUESTS
    result["input_byte_budget_including_retries"] = MAX_INPUT_BYTES
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper", choices=PILOTS)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-public-text-to-gemini", action="store_true", required=True
    )
    args = parser.parse_args()
    try:
        result = asyncio.run(
            evaluate_pilot(
                args.paper,
                args.pdf,
                args.output,
                os.environ["TEST_DOCUMENT_POSTGRES_URL"],
            )
        )
    except EmbeddingError as error:
        raise SystemExit("Gemini evaluation stopped: " + error.code) from None
    print(json.dumps(result["report"], indent=2))


if __name__ == "__main__":
    main()
