"""Offline PDF pilot against a migrated PostgreSQL fixture DB; all rows roll back."""

import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import AccountOwner, DocumentPage, Paper, ResearchDocument
from app.db.models.enums import EvidenceStrength, OwnerKind
from app.documents.contracts import PdfChunk
from app.documents.embeddings import EmbeddingBatch
from app.documents.evaluation import (
    EvaluationDataset,
    EvaluationQuery,
    EvaluationRun,
    evaluate,
)
from app.documents.hybrid import retrieve_hybrid
from app.documents.retrieval import PassageQuery, retrieve
from app.documents.vectors import VectorRepository


@dataclass(frozen=True)
class SemanticInputs:
    documents: EmbeddingBatch
    queries: dict[str, EmbeddingBatch]
    query_embedding_ms: dict[str, float]
    indexing_ms: float


def source_chunks(pages: list[str]) -> list[PdfChunk]:
    chunks = []
    for number, content in enumerate(pages, 1):
        for start in range(0, len(content), 1050):
            end = min(start + 1200, len(content))
            if content[start:end].strip():
                chunks.append(
                    PdfChunk(page=number, start=start, end=end, text=content[start:end])
                )
            if end == len(content):
                break
    return chunks


def load_source(pdf: Path, manifest: dict) -> list[str]:
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != manifest["pdf_sha256"]:
        raise ValueError("PDF hash differs from the frozen label source.")
    # Local public benchmark only; this is NOT the app's upload/scan workflow.
    reader = PdfReader(pdf, strict=True)
    pages = [(p.extract_text() or "").replace(chr(0), "").strip() for p in reader.pages]
    if [hashlib.sha256(p.encode()).hexdigest() for p in pages] != manifest[
        "page_text_sha256"
    ]:
        raise ValueError("Extracted page text changed; review labels before rerunning.")
    for query in manifest["queries"]:
        for evidence in query["evidence"]:
            content = pages[evidence["page"] - 1]
            if not 0 <= evidence["start"] < evidence["end"] <= len(content):
                raise ValueError("Invalid evidence offsets.")
    return pages


async def run(
    pdf: Path, manifest: dict, url: str, semantic: SemanticInputs | None = None
) -> dict:
    if not url.startswith("postgresql+asyncpg://"):
        raise ValueError("The pilot requires PostgreSQL with migrations applied.")
    pages = load_source(pdf, manifest)
    engine = create_async_engine(url)
    runs: list[EvaluationRun] = []
    ids: list[str] = []
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                sessions = async_sessionmaker(connection, expire_on_commit=False)
                async with sessions() as session:
                    owner = AccountOwner(
                        kind=OwnerKind.AUTHENTICATED, auth_subject=str(uuid4())
                    )
                    paper = Paper(
                        title=manifest["title"],
                        normalized_title=str(uuid4()),
                        publication_year=manifest["year"],
                        primary_source_url=manifest["landing_url"],
                        evidence_strength=list(EvidenceStrength)[0],
                        last_verified_at=datetime.now(UTC),
                    )
                    session.add_all([owner, paper])
                    await session.flush()
                    doc = ResearchDocument(
                        owner_id=owner.id,
                        paper_id=paper.id,
                        filename="pilot.pdf",
                        byte_size=pdf.stat().st_size,
                        sha256=manifest["pdf_sha256"],
                        status="ready",
                    )
                    session.add(doc)
                    await session.flush()
                    chunks = source_chunks(pages)
                    ids = [f"{c.page}:{c.start}:{c.end}" for c in chunks]
                    for number, content in enumerate(pages, 1):
                        session.add(
                            DocumentPage(
                                document_id=doc.id,
                                number=number,
                                text=content,
                                chunks=[
                                    {"start": c.start, "end": c.end, "text": c.text}
                                    for c in chunks
                                    if c.page == number
                                ],
                            )
                        )
                    await session.flush()
                    if semantic is not None:
                        await VectorRepository(session).replace(
                            owner.id, doc.id, chunks, semantic.documents
                        )
                    for query in manifest["queries"]:
                        start = perf_counter()
                        result = await retrieve(
                            session,
                            owner.id,
                            doc.id,
                            PassageQuery(query=query["question"], limit=10),
                        )
                        elapsed = (perf_counter() - start) * 1000
                        runs.append(
                            EvaluationRun(
                                query_id=query["id"],
                                engine=result.engine,
                                retrieved=[
                                    f"{p.page}:{p.start}:{p.end}"
                                    for p in result.passages
                                ],
                                citation_valid=[
                                    pages[p.page - 1][p.start : p.end] == p.text
                                    for p in result.passages
                                ],
                                latency_ms=elapsed,
                            )
                        )
                        if semantic is not None:
                            for name in ("gemini_vector", "gemini_hybrid"):
                                start = perf_counter()
                                query_vector = semantic.queries[query["id"]]
                                if name == "gemini_vector":
                                    passages = await VectorRepository(session).nearest(
                                        owner.id, doc.id, query_vector, limit=10
                                    )
                                else:
                                    hybrid = await retrieve_hybrid(
                                        session,
                                        owner.id,
                                        doc.id,
                                        PassageQuery(query=query["question"], limit=10),
                                        query_vector,
                                    )
                                    passages = hybrid.passages
                                runs.append(
                                    EvaluationRun(
                                        query_id=query["id"],
                                        engine=name,
                                        retrieved=[
                                            f"{p.page}:{p.start}:{p.end}"
                                            for p in passages
                                        ],
                                        citation_valid=[
                                            pages[p.page - 1][p.start : p.end] == p.text
                                            for p in passages
                                        ],
                                        latency_ms=(perf_counter() - start) * 1000,
                                    )
                                )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
    dataset = EvaluationDataset(
        name=manifest["name"],
        kind="labelled-corpus",
        passage_ids=ids,
        queries=[
            EvaluationQuery(id=q["id"], relevant=q["relevant"])
            for q in manifest["queries"]
        ],
        runs=runs,
    )
    return {
        "labels": manifest["label_status"],
        "dataset": dataset.model_dump(),
        "report": evaluate(dataset),
        "embedding": None
        if semantic is None
        else {
            "model": semantic.documents.model,
            "dimensions": semantic.documents.dimensions,
            "query_latency_ms": semantic.query_embedding_ms,
            "indexing_ms": semantic.indexing_ms,
        },
        "limitations": "One paper; provisional labels; retrieval-only timing excludes "
        "embedding and PDF processing; exact-slice citation checks are not entailment "
        "checks. No generated answers or general accuracy claim.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evaluation/scikit-learn-public-pilot-v1.json"),
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    url = os.environ["TEST_DOCUMENT_POSTGRES_URL"]
    print(json.dumps(asyncio.run(run(args.pdf, manifest, url)), indent=2))


if __name__ == "__main__":
    main()
