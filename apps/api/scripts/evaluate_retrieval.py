"""Retrieval quality evaluation for Research Bridge AI.

Reports Recall@5, Recall@10, MRR, duplicate rates, and latency
against a small list of benchmark queries via the live OpenAlex pipeline.

Usage:
    cd apps/api
    $env:PYTHONPATH="."
    uv run python scripts/evaluate_retrieval.py
"""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import asyncio
import time

import httpx

from app.db.base import Base
from app.main import create_app

TEST_QUERIES = [
    {
        "query": "transformer efficiency in edge devices",
        "expected_author": "han",
    },
    {
        "query": "quantum error correction surface codes",
        "expected_author": "fowler",
    },
    {
        "query": "explainable ai in medical imaging",
        "expected_author": "rudin",
    },
]


async def main() -> None:
    app = create_app()

    # Create tables in the in-memory SQLite database.
    async with app.state.database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("=== Research Bridge AI: Retrieval Quality Evaluation ===")

    total_latency_ms = 0
    hits_at_5 = 0
    hits_at_10 = 0
    mrr_sum = 0.0
    total_queries = len(TEST_QUERIES)

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with (
        httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client,
        app.router.lifespan_context(app),
    ):
        for i, test in enumerate(TEST_QUERIES):
            query = test["query"]
            expected_author = test["expected_author"].lower()

            print(f"\n[{i + 1}/{total_queries}] Query: '{query}'")

            start_time = time.perf_counter()

            req_payload = {
                "query": query,
                "paper_limit": 20,
                "candidate_limit": 12,
            }
            response = await client.post(
                "/api/v1/discovery/mentors", json=req_payload
            )
            if response.status_code != 200:
                print(f"  Error: {response.status_code} - {response.text}")
                continue

            latency_ms = round((time.perf_counter() - start_time) * 1000)
            total_latency_ms += latency_ms

            data = response.json()
            candidates = data.get("candidates", [])
            print(f"  Returned {len(candidates)} candidates in {latency_ms}ms")

            # --- Duplicate rate ---
            seen_ids: list[str] = []
            duplicates = 0
            total_papers = 0
            for c in candidates:
                for p in c.get("supporting_papers", []):
                    total_papers += 1
                    pid = p.get("openalex_id")
                    if pid:
                        if pid in seen_ids:
                            duplicates += 1
                        else:
                            seen_ids.append(pid)

            duplicate_rate = (
                (duplicates / total_papers * 100) if total_papers > 0 else 0
            )
            print(
                f"  Duplicate Rate: {duplicate_rate:.1f}%"
                f" ({duplicates}/{total_papers})"
            )

            # --- Recall@5, Recall@10, MRR ---
            rank = -1
            for idx, c in enumerate(candidates):
                if expected_author in c.get("display_name", "").lower():
                    rank = idx + 1
                    break

            if rank != -1:
                print(
                    f"  Expected author '{expected_author}'"
                    f" found at rank {rank}"
                )
                if rank <= 5:
                    hits_at_5 += 1
                if rank <= 10:
                    hits_at_10 += 1
                mrr_sum += 1.0 / rank
            else:
                print(
                    f"  Expected author '{expected_author}'"
                    " NOT found in top 12"
                )

            # --- Evidence coverage ---
            if candidates:
                top = candidates[0]
                papers = top.get("supporting_papers", [])
                with_abstract = sum(
                    1 for p in papers if p.get("abstract_snippet")
                )
                evidence_pct = (
                    (with_abstract / len(papers) * 100)
                    if papers
                    else 0
                )
                print(
                    f"  Evidence Coverage: {evidence_pct:.0f}% "
                    f"({with_abstract}/{len(papers)}"
                    " papers with abstracts)"
                )

    print("\n=== SUMMARY ===")
    print(f"Avg Latency: {total_latency_ms / total_queries:.0f}ms")
    print(f"Recall@5:  {hits_at_5 / total_queries * 100:.1f}%")
    print(f"Recall@10: {hits_at_10 / total_queries * 100:.1f}%")
    print(f"MRR:       {mrr_sum / total_queries:.3f}")


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
