"""Post-placement ranking and enrichment evaluation.

This script simulates the performance (Recall, MRR, nDCG@10) of three ranking strategies
on a labeled dataset:
1. Current Phase 7 Heuristic (Keyword + Evidence Depth)
2. PostgreSQL Full-Text Search (tsvector simulation)
3. Vector Similarity Search (pgvector simulation)

Usage:
    cd apps/api
    $env:PYTHONPATH="."
    uv run python scripts/evaluate_ranking_models.py
"""

import math
import time
from dataclasses import dataclass


@dataclass
class LabeledRelevance:
    query: str
    mentor_id: str
    relevance_score: int  # 0 to 3 scale (3 is highly relevant)

@dataclass
class MentorMock:
    id: str
    name: str
    keywords: list[str]
    evidence_depth: int
    vector: list[float]

# 1. Labelled Relevance Set
EVAL_QUERIES = [
    "transformer efficiency in edge devices",
    "quantum error correction surface codes",
    "explainable ai in medical imaging"
]

MENTORS = [
    MentorMock(
        id="m1", name="Dr. Han",
        keywords=[
            "transformer", "efficiency", "edge",
            "devices", "neural networks", "quantization",
        ],
        evidence_depth=15, vector=[0.9, 0.8, 0.2],
    ),
    MentorMock(
        id="m2", name="Dr. Smith",
        keywords=["transformer", "attention", "vision"],
        evidence_depth=5, vector=[0.5, 0.4, 0.1],
    ),
    MentorMock(
        id="m3", name="Dr. Fowler",
        keywords=[
            "quantum", "error correction",
            "surface codes", "qubits",
        ],
        evidence_depth=22, vector=[0.1, 0.9, 0.9],
    ),
    MentorMock(
        id="m4", name="Dr. Rudin",
        keywords=[
            "explainable", "ai", "medical",
            "imaging", "interpretable", "machine learning",
        ],
        evidence_depth=18, vector=[0.8, 0.1, 0.8],
    ),
    MentorMock(
        id="m5", name="Dr. Jones", 
        keywords=["ai", "ethics", "policy"],
        evidence_depth=3, vector=[0.3, 0.2, 0.5]
    ),
]

RELEVANCE_JUDGMENTS = [
    LabeledRelevance(query=EVAL_QUERIES[0], mentor_id="m1", relevance_score=3),
    LabeledRelevance(query=EVAL_QUERIES[0], mentor_id="m2", relevance_score=1),
    LabeledRelevance(query=EVAL_QUERIES[1], mentor_id="m3", relevance_score=3),
    LabeledRelevance(query=EVAL_QUERIES[2], mentor_id="m4", relevance_score=3),
    LabeledRelevance(query=EVAL_QUERIES[2], mentor_id="m5", relevance_score=1),
]


def compute_dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances))

def evaluate_strategy(name: str, ranker_fn) -> None:
    print(f"\nEvaluating Strategy: {name}")
    start = time.perf_counter()
    
    hits_at_5 = 0
    mrr_sum = 0.0
    ndcg_sum = 0.0
    
    for query in EVAL_QUERIES:
        # Get ideal DCG
        ideal_rels = sorted(
            [
                j.relevance_score
                for j in RELEVANCE_JUDGMENTS
                if j.query == query
            ],
            reverse=True,
        )
        idcg = compute_dcg(ideal_rels[:10]) if ideal_rels else 1.0
        idcg = max(idcg, 1e-9)

        # Rank
        ranked_mentors = ranker_fn(query, MENTORS)

        # Evaluate
        rels = []
        rank_of_first_relevant = -1

        for idx, mentor in enumerate(ranked_mentors[:10]):
            rel = next(
                (
                    j.relevance_score
                    for j in RELEVANCE_JUDGMENTS
                    if j.query == query
                    and j.mentor_id == mentor.id
                ),
                0,
            )
            rels.append(rel)
            if rel >= 2 and rank_of_first_relevant == -1:
                rank_of_first_relevant = idx + 1
                
        if rank_of_first_relevant != -1:
            if rank_of_first_relevant <= 5:
                hits_at_5 += 1
            mrr_sum += 1.0 / rank_of_first_relevant
            
        dcg = compute_dcg(rels)
        ndcg_sum += (dcg / idcg)
        
    latency = (time.perf_counter() - start) * 1000
    n = len(EVAL_QUERIES)
    
    print(f"  Latency:    {latency:.2f}ms")
    print(f"  Recall@5:   {hits_at_5 / n * 100:.1f}%")
    print(f"  MRR:        {mrr_sum / n:.3f}")
    print(f"  nDCG@10:    {ndcg_sum / n:.3f}")

# --- Ranking Strategies ---

def heuristic_ranker(query: str, mentors: list[MentorMock]) -> list[MentorMock]:
    """Simulates Phase 7: exact keyword match counting + evidence depth weight."""
    query_terms = set(query.lower().split())
    def score(m: MentorMock) -> float:
        matches = sum(1 for k in m.keywords if any(t in k.lower() for t in query_terms))
        return (matches * 0.5) + (m.evidence_depth * 0.05)
    return sorted(mentors, key=score, reverse=True)


def tsvector_ranker(query: str, mentors: list[MentorMock]) -> list[MentorMock]:
    """Simulates PostgreSQL full-text search with BM25-like behavior."""
    query_terms = set(query.lower().split())
    def score(m: MentorMock) -> float:
        # tf-idf approximation
        tf = sum(1 for k in m.keywords if any(t in k.lower() for t in query_terms))
        return tf / (len(m.keywords) + 1)
    return sorted(mentors, key=score, reverse=True)


def pgvector_ranker(query: str, mentors: list[MentorMock]) -> list[MentorMock]:
    """Simulates pgvector cosine similarity."""
    # Mocking a vector mapping for the queries
    query_vectors = {
        EVAL_QUERIES[0]: [0.9, 0.7, 0.1],
        EVAL_QUERIES[1]: [0.2, 0.8, 0.9],
        EVAL_QUERIES[2]: [0.85, 0.2, 0.85],
    }
    qv = query_vectors.get(query, [0.0, 0.0, 0.0])

    def cosine_sim(v1, v2):
        dot = sum(
            a * b for a, b in zip(v1, v2, strict=True)
        )
        mag1 = math.sqrt(sum(a * a for a in v1))
        mag2 = math.sqrt(sum(b * b for b in v2))
        return dot / (mag1 * mag2) if mag1 and mag2 else 0.0

    def score(m: MentorMock) -> float:
        # Simulate network latency of embedding generation
        time.sleep(0.01)
        return cosine_sim(qv, m.vector)

    return sorted(mentors, key=score, reverse=True)


if __name__ == "__main__":
    print("=== Phase 14: Ranking & Enrichment Evaluation ===")
    evaluate_strategy("Phase 7 Heuristic", heuristic_ranker)
    evaluate_strategy("PostgreSQL tsvector (FTS)", tsvector_ranker)
    evaluate_strategy("pgvector (Cosine Similarity)", pgvector_ranker)
    print(
        "\nConclusion: Vector similarity introduces "
        "embedding latency but can improve nDCG."
    )
    print(
        "For a localized dataset without cross-encoder "
        "reranking, heuristic + depth provides the best "
        "latency/complexity trade-off."
    )
