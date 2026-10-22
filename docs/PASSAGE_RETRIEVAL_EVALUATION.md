# Passage retrieval baseline evaluation

This is a tiny synthetic regression fixture, not a research-quality benchmark.
No real student documents or external AI providers were used.

Fixture: three short pages about graph attention, held-out molecular evaluation,
and dataset limitations (tests/test_document_retrieval.py).

SQLite lexical baseline results on 2026-10-15:
- Three answerable keyword queries: expected page ranked first in 3/3 cases.
- Three unrelated/stopword/punctuation queries: zero passages in 3/3 cases.
- Every returned excerpt matched its exact stored page slice.
- Separate regression excludes overlapping chunks and forged offsets.

These queries share words with the source and do not measure semantic understanding,
scientific answer quality, Recall@10 on realistic corpora, or production latency.
No generated answers exist, so answer citation support is not yet measured.

PostgreSQL full-text ranking remains unmeasured. The local Docker engine was
unavailable. To validate: use a disposable PostgreSQL database, apply Alembic head,
set TEST_DOCUMENT_POSTGRES_URL to its asyncpg URL and run:

    uv run pytest tests/test_document_retrieval_postgres.py -q

The integration test requires the GIN index and rolls back fixture records. Never
publish SQLite results as PostgreSQL results. Future evaluation needs representative
full papers, labelled relevant passages, paraphrases, unsupported questions and
latency measurements before tuning hybrid pgvector retrieval.

Implementation references:
- https://www.postgresql.org/docs/17/textsearch-controls.html
- https://www.postgresql.org/docs/16/textsearch-tables.html


### Verified PostgreSQL retrieval and passage-search UI
PostgreSQL integration passed on a freshly migrated temporary database, including
GIN index presence, ready-state/ownership checks, exact page slices, all three
expected first-page matches and three no-match queries. Test database removed.
These remain tiny synthetic smoke tests, not general retrieval accuracy claims.
The extracted-text reader now offers keyword passage search, loading/error/no-match
states and keyboard-accessible source-page buttons. Excerpts remain plain text;
no AI answer is implied. No dependency or schema change beyond migration 0009.


### Hybrid passage retrieval baseline (2026-10-19)
Added app/documents/hybrid.py: owner-scoped keyword and vector candidates are
combined using equal-weight reciprocal rank fusion (fixed k=60). Each retriever
supplies at most ten candidates; output is limited to one through ten passages.
Duplicate candidates cannot inflate a ranking, overlapping excerpts are suppressed,
and every returned page/offset is rechecked against stored text. Stable page/offset
ties make results reproducible. Rank is not confidence or evidence of an answer.
No dependency, schema, endpoint or frontend change. Query embeddings are supplied
by the caller; there are no external provider calls in this service.
PostgreSQL integration passed on a disposable migrated database, removed afterward.
Synthetic vectors verify fusion and ownership mechanics, not semantic quality.
Next: explicit query disclosure and committed usage reservations before query
embedding calls, followed by representative retrieval evaluation and cited answers.


### Reproducible passage evaluation tooling (2026-10-19)
Added an offline labelled-run evaluator and CLI. It computes macro Recall@5/10,
MRR and binary nDCG@10 for answerable queries; unsupported-query retrieval rate is
reported separately. Duplicate and citation-coverage rates use retrieved rows;
no retrieved rows yields null, not a misleading perfect score. Latency p50/p95 use
nearest-rank percentiles on supplied observations. Duplicate passages and citations
marked invalid receive no relevance credit. All engines must cover identical queries;
unknown passage references, duplicate labels/runs and nonfinite timings are rejected.
No new dependency, API, migration or live provider request.

The included two-query synthetic fixture validates arithmetic only. Its rankings,
latencies and citation-audit flags are supplied test data, not production measurements.
Real-paper semantic quality, generated-answer citation support and unsupported-claim
rate remain unmeasured. This tool does not itself audit source text or run retrieval.
Next: gather reviewed passage labels and actual keyword/vector/hybrid exports on the
same public-paper corpus, then evaluate before tuning ranking or adding answers.


## Real-paper benchmark protocol (not yet executed)
1. Select 12 reusable open-access text PDFs across three research areas. Record DOI,
   source URL, licence, PDF hash and extraction version. Exclude private uploads.
2. Write four questions per paper: exact terminology, paraphrase, a limitation, and
   an intentionally unsupported question. Keep development and held-out papers
   separate. Do not tune fusion parameters on held-out queries.
3. Review all candidate passages for each question and assign relevant passage IDs
   using document hash, page and offsets. A second review should resolve ambiguous
   labels; absent review, clearly label the dataset as single-reviewer provisional.
4. Run PostgreSQL FTS, vector and hybrid retrieval on identical document snapshots,
   queries and top-10 limits. Record model/dimensions and fixed fusion k=60. Keep
   query embedding and retrieval timings separate in raw observations; identify
   which timing is exported. Never substitute fabricated embeddings for quality runs.
5. Audit each returned citation against the stored source slice; export the result
   in citation_valid. Preserve duplicates and ordering so metrics can detect them.
   Include completed no-match queries with empty rankings. Report failed requests
   separately; do not omit them silently or label failures as no-match outcomes.
6. Run scripts.evaluate_paper_passages on the exported dataset. Publish the corpus
   manifest, label provenance, failed-request count, sample counts and environment
   with the report. Treat p95 from small samples as descriptive only.

The synthetic JSON demonstrates the file format only. It is not a substitute for
this protocol and should not supply resume or public accuracy claims. Retrieval
results cannot establish that generated answers are faithful: that requires a
separate claim-to-citation evaluation after answer generation is implemented.


### First public-paper retrieval pilot (2026-10-19)
Ran production PostgreSQL FTS against the six-page 2011 Scikit-learn paper by
Pedregosa et al. Publisher source: https://www.jmlr.org/papers/v12/pedregosa11a.html
The fixture stores source attribution, PDF/page-text hashes, questions and evidence
offsets, not the PDF. Labels were frozen before retrieval and are provisional,
single-agent-reviewed (not human gold labels). Four answerable and two unsupported
questions were evaluated on all extracted chunks. The temporary database was removed.

Observed FTS Recall@5/10, MRR and binary nDCG@10: 0.75 each. Three labelled passages
ranked first; the paraphrased nearest-neighbour question missed its evidence.
Duplicate rate: 0; exact source-slice citation coverage: 1.0. Both unsupported
questions returned passages (unsupported-query retrieval rate 1.0). No answers were
generated, so this is not a hallucination measurement. Six local retrieval-only
observations gave p50 10.30 ms and p95 24.73 ms; these are not production latency
estimates and exclude embedding/network/PDF processing.

No ranking parameter was tuned on this pilot. One paper and provisional labels do
not establish general accuracy. No semantic/vector/hybrid quality run was made;
no provider call or private student document was used. The next step is a reviewed,
broader corpus and real semantic comparison before claiming measured improvement.
The observed unsupported matches also motivate explicit answer-support checks.


### Two-paper keyword pilot (2026-10-19)
Added a LIBLINEAR public-paper pilot (Fan et al., 2008), with six questions frozen
before running PostgreSQL FTS. Source: https://www.jmlr.org/papers/v9/fan08a.html
All four answerable evidence spans were retrieved; both unsupported questions
returned passages. Combined with the Scikit-learn pilot: 12 questions, 8 answerable,
4 unsupported; Recall@5/10 0.875, MRR 0.6875, binary nDCG@10 0.7366. No exact duplicate
passages; all returned slices matched stored text. Unsupported-query retrieval rate
was 1.0. This is not generated-answer accuracy or citation entailment.

Added combine_datasets and a repeatable combine_paper_pilots CLI. Paper-local query
and passage identifiers are namespaced; duplicate paper names and missing engine
coverage fail validation. The command exactly reproduced saved combined metrics.
No production ranking changes were tuned to these results. Both papers are from the
same domain, with provisional agent-reviewed labels, so this is not a representative
or human-labelled benchmark. Original run timings are retained, not remeasured.

Configuration check found no server embedding API key and indexing disabled.
Semantic comparison remains unrun; no fake vectors or live AI calls were used.
LIBLINEAR PDF extraction emitted missing-fontTools warnings for some fonts. Evidence
questions use reviewed prose, excluding equations/figure labels, and extracted-page
hashes preserve the tested output. No new dependency was installed to alter extraction.
Next: configure the server-side embedding provider securely and run a bounded public
paper semantic comparison; expand to reviewed cross-domain labels before public claims.
