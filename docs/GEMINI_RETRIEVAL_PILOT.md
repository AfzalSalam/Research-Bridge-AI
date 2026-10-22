# Public-paper Gemini retrieval pilot — 20 October 2026

This is a small development pilot, not a general accuracy claim. It uses two
machine-learning papers (Scikit-learn and LIBLINEAR), eight answerable questions
and four unsupported questions. Evidence labels were frozen before retrieval and
remain provisional, agent-reviewed labels rather than independent human gold labels.

| Retrieval method | Recall@5 | Recall@10 | MRR | nDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| PostgreSQL keyword | 0.875 | 0.875 | 0.6875 | 0.7366 |
| Gemini vector | 1.000 | 1.000 | 0.8750 | 0.9077 |
| Existing hybrid | 0.875 | 0.875 | 0.8125 | 0.8289 |

Gemini found labelled evidence for all eight answerable queries in its first five
passages; keyword and hybrid retrieved seven. Keyword rankings exactly reproduce
the earlier pilots. The saved combined metrics reproduce from the individual outputs.
All engines returned passages for all four unsupported queries. That is retrieval
behavior, not hallucination: no answers were generated. The answer stage still needs
an explicit evidence-support/abstention check.

All returned excerpts matched stored source slices; exact duplicate rate was zero.
These checks validate offsets/text integrity, not semantic support for generated claims.
Each paper has only 11 or 17 chunks: top-10 recall is particularly easy on this corpus.
Both papers share a domain; do not advertise these results as product-wide accuracy.

## Observed hybrid failure

For the Scikit-learn nearest-neighbour question, the labelled evidence occupies
page 5 offsets 659–836, within chunk 5:0:1200. Gemini ranks that chunk first.
The existing fusion orders neighbouring chunk 5:1050:2250 ahead of it, then removes
the relevant chunk because the two chunks overlap by 150 characters. The retained
chunk does not contain the labelled evidence. No labels or ranking parameters were
changed after seeing this result. Next, test overlap handling independently using
synthetic adjacent-chunk cases and a broader held-out corpus before choosing a fix.

## Timing and boundaries

Database retrieval-only p50/p95: keyword 17.54/21.44 ms, vector 21.17/28.61 ms,
hybrid 51.89/59.08 ms. These are single local observations, not production estimates;
engine order was fixed, and cache effects are not controlled. They exclude Gemini
calls, PDF extraction and indexing. Query embeddings are measured separately below.
Document preparation time includes deliberate two-second pacing between requests.

Only public PDF text and benchmark questions went to Gemini: 28 document chunks and
12 questions, using gemini-embedding-2 at 1536 dimensions. No private PDFs, CVs or
Gmail messages were used. Each paper has a preflight cap of 100 logical inputs and
200,000 UTF-8 bytes including prefixes and three allowed transport attempts. Long
Retry-After errors stop the pilot; there is no outer retry loop. Database writes
ran inside rolled-back fixture transactions, and the disposable database was removed.
The private upload, scanning and consent workflow was not exercised by this benchmark.

LIBLINEAR retains the previously documented fontTools extraction warnings; source
PDF and extracted-page hashes matched the frozen manifests. Labels cover reviewed
prose, not equations or figure text. No dependency was added to change extraction.
Provider updates can change future vectors; raw rankings and run timestamps are kept.

## Reproduce

From apps/api, with a migrated disposable TEST_DOCUMENT_POSTGRES_URL and server-only
GEMINI_API_KEY, use the existing hash-matching public PDF copies:

```powershell
uv run python -m scripts.run_gemini_paper_pilot scikit-learn .test-tmp-public-papers/scikit-learn.pdf --output evaluation/scikit-learn-gemini-pilot-results-v1.json --allow-public-text-to-gemini
uv run python -m scripts.run_gemini_paper_pilot liblinear .test-tmp-public-papers/liblinear.pdf --output evaluation/liblinear-gemini-pilot-results-v1.json --allow-public-text-to-gemini
uv run python -m scripts.combine_paper_pilots evaluation/scikit-learn-gemini-pilot-results-v1.json evaluation/liblinear-gemini-pilot-results-v1.json --name public-two-paper-gemini-pilot-v1
```

The first two commands call Gemini; the aggregation command is offline. Source URLs,
PDF/page hashes and frozen evidence offsets are in the matching public-pilot manifests.
No production search policy, frontend, schema or feature flag changed in this step.

Query embedding latency p50: 560.26 ms; p95: 623.39 ms (12 observations).


### Evidence-preserving overlap fix (2026-10-20)
Hybrid fusion now suppresses a passage only when an already selected passage
fully contains its source interval on the same page. Partial overlap retains
distinct source text. RRF weights, tie order, result limits and citation validation
are unchanged; no percentage threshold was tuned to the benchmark.

Independent tests cover 1/150/1199-character overlaps, contained spans, extensions,
cross-page spans, result caps and agreement across rankings. Offline replay of the
unchanged public keyword/vector rankings recovered all eight labelled answers in
the first five results (previous hybrid: seven); MRR 0.8375, nDCG@10 0.8772.
Exact duplicate rate remains zero; partially repeated text is now intentionally
possible. All four unsupported queries still retrieve passages. No new Gemini
calls were made. This is observed-data regression evidence, not held-out accuracy.

Files: apps/api/app/documents/hybrid.py, tests/test_document_hybrid.py,
scripts/replay_hybrid_pilot.py and evaluation/public-hybrid-containment-replay-v1.json.
Reproduce from apps/api with `uv run python -m scripts.replay_hybrid_pilot`; it checks
public PDF/page hashes and uses saved rankings. Replay timing is fusion-only, not
database or network latency. Existing font extraction warnings remain documented.

Next: implement evidence-support validation and explicit insufficient-evidence
responses before generated paper answers; broaden held-out retrieval evaluation.
