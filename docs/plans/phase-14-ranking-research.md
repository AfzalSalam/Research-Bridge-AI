# Phase 14 — Post-placement Ranking and Enrichment Research

## Goal Description
Evaluate the complexity and benefit of PostgreSQL full-text retrieval, `pgvector`, and embedding strategies against the current heuristic-based ranking. The roadmap specifies adopting this complexity *only* if measurements show a tangible benefit in metrics like MRR and nDCG@10.

## Proposed Changes

### 1. Research & Evaluation Script
#### [NEW] `scripts/evaluate_ranking_models.py`
- Create a sandbox script that loads a synthetic benchmark dataset of mentors and papers.
- Implement baseline retrieval (Current Phase 7 Heuristic).
- Implement simulated `tsvector` (Full-Text Search) retrieval.
- Implement simulated `pgvector` (Cosine Similarity) retrieval via mock embeddings.
- Calculate Recall@5, Recall@10, MRR, and nDCG@10 for all three strategies.

### 2. Research Report
#### [NEW] `docs/research/ranking-evaluation.md`
- Document the methodology, metrics, latency tradeoffs, and complexity costs.
- Provide a final decision on whether to adopt PostgreSQL full-text search and `pgvector` into the live production application at this stage.

## Verification Plan
### Automated Tests
- The script should run successfully and output a clear metrics table comparing the strategies.
### Manual Verification
- Review the markdown report to ensure it adheres to the roadmap constraint: "Adopt complexity only when measurements show a benefit."
