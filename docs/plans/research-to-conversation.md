# Research to conversation - approved 2026-10-11

Implement in the Desktop checkout. Preserve existing work and private data.

1. Connect the journey: academic default, 10/20/30 targets, account-persisted
research collections and notes, exact catalog paper/author handoff, contact-to-
draft transfer and restoration. Test before phase 2.
2. Private PDF reading: quarantine/scan, text extraction, page chunks, FTS and
pgvector retrieval, cited answers, limits 20 MB/100 pages, explicit unsupported states.
3. Gmail: independent OAuth/PKCE connection, encrypted refresh tokens, optional
private 5 MB PDF CV, approved links, version-bound reviewed sends, immutable
snapshots and duplicate/unknown-outcome protection.
4. Conversations: background Pub/Sub + periodic reconciliation, durable jobs,
threaded manual replies, unread state, manual reminder dates, Gmail fallback.
5. Public release: ownership/deletion/abuse checks, quality measurements,
production setup guide, Google verification materials, backups/restore and E2E.

Primary UI: Discover, My Research, Conversations, Opportunities, Profile & Settings.
Retain evidence and source dates; never infer professors, openings or addresses.
No bulk/automatic sending, automatic follow-ups, OCR or AI access to Gmail replies.
Keep modular monolith; worker uses same code and Postgres jobs, no Celery.
Private storage and Gmail require owner-provided provider configuration; never
pretend an unconfigured integration sends mail. Test real email only with explicitly
selected consenting mailboxes. Public launch requires Google approval where applicable.

Status: phase 1 connected journey implemented and tested, including bounded early
contact checks and exact DOI/arXiv citation matching. Latest frontend validation:
81 unit tests, 15 browser tests, lint, typecheck and production builds passed.
Docker services are healthy. Phase 2 ingestion primitives implemented; storage,
worker, UI and retrieval pending. Phases 3-5 pending. Gmail is not configured.
Owner requested setup instructions; preparation is documented in docs/GMAIL_SETUP.md.


## Current increment: early contact discovery
Before PDF/Gmail phases, surface public-email availability beside academic papers.
Reuse the authenticated contact API and official evidence; no new dependencies.
Automatically check at most six distinct authors, corresponding authors first and
round-robin across papers, with two concurrent requests. Preserve results across
navigation, reuse them in the detailed contact view, allow cancellation/restart,
and show incomplete/failed checks separately from completed no-match results.
Add an optional contactable-author filter without changing relevance order.
Do not claim exhaustive contact coverage or professor status. Defer visual redesign.
Validate queue limits/deduplication, failure states, filter and exact author links;
run frontend gates and browser fixtures. Document the bounded first-pass limitation.

Early contact increment: implemented; 68 unit tests and 15 browser flows pass,
alongside lint, typecheck and production build. Docker web image refreshed; all
four local services are healthy.


## Current increment: arXiv citation resolution
Parse exact arxiv.org abstract/PDF URLs (modern and legacy identifiers), normalize
version suffixes to the canonical arXiv DOI, and reuse authenticated DOI discovery.
Only exact DOI equality enables the catalog handoff; no title-based identity guess.
Retain original website citation/version evidence and explain canonical matching.
Persist resolution across navigation. Test malformed/spoofed URLs, normalization,
versions and mismatch states. Reference: https://info.arxiv.org/help/doi.html.
No new dependency/schema required.

Citation increment verified and deployed locally; next phase is private PDF reading.


## Phase 2 execution: private paper reading
1. Build and test ingestion primitives: 20 MB/100-page limits, ClamAV fail-closed
   scanning, subprocess extraction with CPU/memory/time limits, numbered pages and
   bounded within-page chunks. No OCR, encrypted PDFs or embedded active content.
2. Wire private Supabase quarantine/storage, owner-scoped document/page/job records,
   additive migration, durable worker leases/retries, deletion and processing API.
3. Add upload/reader/status UI, owner-authorized document access, and source-backed
   questions with FTS/pgvector retrieval. Evaluate retrieval/citations with fixtures.
4. Validate ownership, failures, malicious/unsupported PDFs, refresh and mobile use;
   update contracts/docs and deploy only configured features.
New dependency pypdf is for text extraction only; antivirus uses ClamAV INSTREAM
protocol through Python stdlib. Unscanned files must never be parsed or previewed.
No LLM receives CVs or Gmail data. Phase 2 is in progress, not complete.


### Current phase-2 increment: durable document lifecycle
Add owner-scoped document, page and processing-job tables with an additive migration.
Use UUID storage keys, private Supabase bucket checks and bounded authenticated
storage transport. Persist upload intent before external storage writes; no preview
until ready. Lease processing jobs using PostgreSQL SKIP LOCKED and fencing tokens,
with bounded retries and crash recovery. Test cross-owner denial and stale leases.
Expose only configured operations; keep upload disabled until cleanup/deletion,
worker, scanner and storage wiring are complete. No public PDFs or bypass scanner.


Durable database portion complete: migration/models/repository and five regression
tests. Full backend: 174 passed; Ruff/mypy passed. PostgreSQL smoke verified actual
SKIP LOCKED concurrency, expiry/fencing and page persistence, with fixture cleanup.
Local API rebuilt and migration applied; four Docker services healthy. Remaining
in this increment: private storage adapter, upload intent/cleanup, worker loop,
and authorized processing endpoints. Do not expose uploads before these are ready.


### Next increment: private object transport and worker orchestration
Implement an authenticated Supabase Storage adapter with UUID-only object paths,
private-bucket verification, bounded streams/timeouts and no public URL generation.
Add an independent blob ledger so account/document cascades cannot erase cleanup
work. Register the ledger before uploads; delay orphan cleanup past upload timeout,
lease and retry deletion independently. Connect hash checking, scanning and parsing
to the existing durable processing jobs. Test network failures, public buckets,
orphan cleanup and stale worker outcomes with fixtures before any upload API.
Keep private credentials server-only and document the still-required service setup.


2026-10-15: storage/worker increment implemented and tested. Durable upload service
commits intent/cleanup before network writes; separate cleanup ledger survives
account deletion. Worker handles hash mismatch, scanner failures and cancellation.
20 new fixture tests pass; complete backend suite 194 passed; lint/types clean.
Next: authenticated upload/status/delete/download endpoints with request size and
rate limits, typed contracts and reader UI, followed by evaluated cited retrieval.
Live bucket/scanner validation is still required before advertising PDF uploads.

Local validation completed: API image rebuilt; migration 20261012_0008 applied.
PostgreSQL smoke verified AccountDeletionService cascades while retaining cleanup
intent, concurrent SKIP LOCKED behavior, expired-claim recovery and stale completion
rejection. Temporary fixtures removed; worker --status reports empty queues.
All four Docker services healthy. This did not contact live Storage or antivirus.


### Authenticated PDF interface increment (2026-10-15)
Add owner-scoped upload/list/status/pages/delete APIs with bounded raw PDF bodies,
explicit enablement and persisted per-owner upload throttling. Authentication
commits its owner record before the upload service opens independent transactions.
Add paper-workspace upload/status controls and a safe numbered-page text view.
Keep live uploads off by default until Storage/scanner/worker are configured.
Validate account isolation, request limits and setup-disabled behavior; regenerate
contracts and run backend/frontend gates. Original PDF access and cited Q&A follow.


Authenticated interface increment verified: 197 backend, 84 frontend unit and 16
browser tests pass; lint, types, production build and generated contracts pass.
Upload/status/delete and numbered extracted text are connected to paper workspace.
Default enablement remains off. Original PDF viewing, OA fetch and evaluated cited
retrieval remain phase-2 work; no Gmail phase has started.

Local API and web images rebuilt and refreshed; all four Docker services passed
health checks. Live OpenAPI includes the document routes. Upload enablement remains
off. Docker dependency installation reported 14 audit findings (3 moderate,
10 high, 1 critical); impact/production reachability was not evaluated in this
increment and needs dependency triage before public launch. No forced upgrades.


### Original PDF access increment (2026-10-15)
Add an authenticated ready-only original-file endpoint through the existing private
storage adapter. Check ownership before storage access, verify the scanned SHA-256,
and recheck ownership/status after download. Return private/no-store PDF responses
with defensive browser headers; never expose storage credentials or public URLs.
Test quarantine, cross-account denial, tampering and provider failure. No schema or
dependency change. Reader integration and cited retrieval follow this prerequisite.


### Original PDF access (2026-10-15)
Added authenticated GET /documents/{id}/file for ready documents. The service
checks ownership before fetching, SHA-256 against the scanned bytes, and ownership
and readiness again after fetching. Responses use private/no-store caching and
defensive PDF headers. Storage failures return a safe 503; altered files return
409. No migration or dependency added. Original-reader UI integration, open-access
fetching and cited retrieval remain pending; uploads remain disabled by default.


### Reader integration increment
Fetch original PDFs with bearer authentication only on explicit request. Keep bytes
out of persisted query/browser storage; revoke object URLs and abort requests on
close, document change or account unmount. Show native PDF preview with a download
fallback, retry state and existing extracted-text access. Test lifecycle and errors;
run frontend gates and browser flows. No dependency or migration required.


### Original PDF reader integration (2026-10-15)
Ready PDFs now offer an explicit original-file viewer and download fallback alongside
extracted text. Bearer-authenticated fetch uses no-store; temporary blob URLs are
revoked on close/unmount, pending fetches abort, and query bytes expire immediately
after the reader unmounts. Account identity changes already remount the private
workspace. No dependency or migration added. Browser-native PDF support varies;
the sandboxed preview may require using the download fallback. Live uploads remain
disabled pending Storage/ClamAV validation. Cited Q&A and OA fetching remain pending.

Reader validation complete: production build and all 16 Playwright flows passed,
including PDF failure/retry controls, extracted-text accessibility and mobile layout.
Full frontend lint and typecheck passed. Original PDF visual rendering with a real
scanned file remains unverified; fixture tests cover URL cleanup and cancellation.


### Passage retrieval baseline
Add owner/ready-scoped passage search with PostgreSQL full-text page prefilter and
chunk ranking, exact page offsets and excerpts. Add a GIN expression-index migration.
Use bounded normalized keyword queries and parameter binding, never generated SQL.
Return passages or explicit no-match; no generated answer or confidence percentage.
SQLite tests use an explicitly labelled lexical fallback, not simulated PostgreSQL.
Evaluate exact citation support, answerable/unanswerable fixture retrieval, ownership
and quarantine; exercise PostgreSQL separately. Embeddings and Q&A follow baseline.


### Passage retrieval baseline (2026-10-15)
Added POST /documents/{id}/passages with owner/ready checks, bounded normalized
keywords, exact page/offset excerpts, overlap suppression and explicit no-match.
PostgreSQL uses simple-config full-text page filtering and chunk ranking; migration
20261015_0009 adds a GIN expression index. SQLite uses a labelled lexical fallback.
This returns evidence passages only, not generated answers or semantic retrieval.
No dependency added. pgvector embeddings, cited Q&A and the question UI remain pending.
201 backend tests pass; later endpoint checks pass (6 tests); Ruff/mypy pass.
Real PostgreSQL integration is pending: Docker engine unavailable, and the opt-in
TEST_DOCUMENT_POSTGRES_URL test skipped. Migration is not applied to live PostgreSQL.


### Passage-search reader integration
While PostgreSQL startup is checked, connect the existing passage API to the ready
text reader. Use RHF/Zod validation, TanStack mutations, explicit search and no-match
/error states; render excerpts as text and link to their numbered source page.
Keep this distinct from Q&A. Test page navigation, unsupported queries, unsafe text
and browser accessibility; no new schema or dependency.


### Verified PostgreSQL retrieval and passage-search UI
PostgreSQL integration passed on a freshly migrated temporary database, including
GIN index presence, ready-state/ownership checks, exact page slices, all three
expected first-page matches and three no-match queries. Test database removed.
These remain tiny synthetic smoke tests, not general retrieval accuracy claims.
The extracted-text reader now offers keyword passage search, loading/error/no-match
states and keyboard-accessible source-page buttons. Excerpts remain plain text;
no AI answer is implied. No dependency or schema change beyond migration 0009.


Prior increment completion (recorded 2026-10-17): 90 frontend tests and all 16
Playwright flows passed, alongside lint/typecheck/build. PostgreSQL fixture test
passed; API/web images refreshed, four services healthy and migration 0009 applied
at the end of that run. Final log append was interrupted by automatic approval
review hitting a usage limit, not a safety rejection.

### Semantic retrieval provider foundation
Implement a bounded embeddings adapter using the existing HTTPX client dependency.
Pin model/dimension metadata, limit inputs, validate every returned vector/index,
refuse non-finite or zero vectors, bound response bytes and retries, honor provider
rate limits, and never log input text or credentials. Test with HTTP fixtures only.
Keep it unconnected to uploads until owner-scoped vector persistence, usage quotas
and student disclosure are implemented. No live private-document calls.


### Semantic retrieval provider foundation (2026-10-17)
Added an isolated OpenAI embeddings adapter for text-embedding-3-small, fixed at
1536 dimensions. It bounds batches (32 passages of at most 1200 characters),
response size (4 MiB), request duration and retries; rejects redirects, malformed
indices, mismatched models, non-finite/zero vectors, and preserves input order.
Returned vectors are normalized and include model/dimension/token-use metadata.
No new dependency, migration, route or UI change. The adapter is not wired to
uploads or queries yet: no private document text has been sent to OpenAI.
Next: owner-scoped pgvector persistence, usage reservations and student disclosure,
then hybrid retrieval evaluation and cited Q&A. Existing keyword search is unchanged.

Embedding adapter validation: Ruff clean; mypy clean (134 files); full backend
suite 228 passed, 1 optional PostgreSQL test skipped because its URL was unset.
27 new embedding tests use HTTP fixtures. No frontend change, new schema, live
provider call or Docker deployment was needed for this unconnected adapter.


### Vector persistence increment (2026-10-17)
Add pgvector-backed page-chunk embeddings with source offsets/hash and pinned model
metadata, via additive migration. Use SQLite JSON only for lifecycle tests.
Validate exact source chunks and model/dimension before writes; lock the owned ready
document against concurrent reprocessing/deletion. Search must include owner/document
filters and return only source-verified excerpts. Cascade page/document deletion.
Add pgvector Python integration for SQLAlchemy vector serialization/operators.
No live embedding calls, usage endpoint or automatic indexing until quotas and
disclosure are implemented. Validate migration/vector ranking on temporary PostgreSQL.


### Account-owned vector storage (2026-10-17)
Added migration 20261017_0010 and DocumentVector records attached to private pages.
Each vector retains offsets, source-text SHA-256 and model; PostgreSQL enforces
1536 dimensions. Full-document replacement validates every stored chunk before
changing the prior index. Exact cosine search filters owner/document/readiness/model
and verifies current source text before returning excerpts. Deleting pages/documents
cascades vectors. SQLite stores JSON only for lifecycle tests and refuses vector search.
Added pgvector 0.5.1 (SQLAlchemy serialization and operators); no approximate index
or new service. Real PostgreSQL migration, rollback/reapply, ranking, isolation and
deletion tests passed on a temporary database, which was removed. Synthetic unit
vectors test ordering mechanics, not semantic quality. Worker/API wiring, quotas,
disclosure and hybrid evaluation remain pending; no private text sent to AI.

Vector increment final gates: Ruff clean, mypy clean (136 files), full suite
234 passed with 1 default opt-in PostgreSQL skip. The same PostgreSQL integration
test was explicitly run separately against a temporary pgvector database and
passed, including migration downgrade/reapply. No frontend/API contract changed.


### Durable semantic indexing and usage reservations
Add one indexing job per document, explicit disclosure acceptance, fenced leases,
three bounded attempts and owner-serialized daily token reservations. Charge a
conservative UTF-8-byte upper bound including provider retry allowance before
network calls; retain reservations on failure/unknown outcome and document deletion.
Owner deletion removes reservations. Use a separate indexing worker service with
fixture provider tests; no public route/automatic invocation until disclosure UI.
Successful completion and full-vector replacement share a transaction. Preserve
text-reader availability on embedding failures. No new dependency.


### Durable semantic indexing foundation (2026-10-17)
Added migration 0011: one semantic-index job per document and owner-scoped daily
usage reservations. Enqueue requires disclosure acceptance; leases are fenced,
renewed per batch, and capped at three attempts. Reservation uses conservative
UTF-8-byte/token bounds plus provider retry allowance before external calls.
Reservations survive document deletion and failed/unknown outcomes; account deletion
removes them. Quota exhaustion defers until the next UTC day; documents exceeding
the entire daily budget fail explicitly. Index completion and vector replacement
share a transaction. Embedding failures do not remove ready text/PDF access.
The worker service is tested with fixtures; no public enqueue endpoint, disclosure
UI or continuously running indexing worker is enabled yet. No live AI calls made.
PostgreSQL integration and migration rollback/reapply passed on a temporary database.

Final indexing gates: Ruff clean, mypy clean (139 files), backend suite 240 passed
with one default opt-in PostgreSQL skip. That integration test passed separately
on temporary PostgreSQL, including 0011 downgrade/reapply. No frontend contract
change or live provider call. Multi-connection quota contention stress testing
remains part of worker rollout; current integration validates sequential lifecycle.


### Indexing consent/status interface and worker configuration
Expose owner-scoped status, explicit version-bound consent enqueue and cancellation.
Gate new indexing by server enablement, API key and PostgreSQL; off by default.
Add status polling and clear data-sharing disclosure to the ready-paper reader.
Cancellation fences the lease and prevents future batches, while explaining an
in-flight provider call cannot be recalled. Add a CLI status/once/loop worker.
Regenerate contracts and test consent, cross-owner denial, setup-off, cancellation,
frontend states and browser flows. No live AI calls during validation.


### Indexing consent interface validated and deployed (2026-10-19)
The ready-paper reader now exposes owner-scoped indexing status, explicit unchecked
version-bound consent, and cancellation. Enqueue is idempotent. Server enablement,
PostgreSQL and an AI key gate the feature; it remains disabled by default.
Cancellation fences future batches and preserves conservative usage reservations;
an in-flight provider request cannot be recalled. The worker has status/once/loop
commands but is not automatically started by Compose. No new dependency was added.

Validation: the interrupted browser run's saved result confirms success with no
failed tests. Prior frontend gates passed (93 unit tests, lint, typecheck, generated
contracts and production build). Prior full backend run passed 240 tests with one
opt-in PostgreSQL skip; all 8 indexing tests, including the two subsequent CLI and
cancellation cases, passed on October 19. Ruff and mypy had passed. Docker API/web
builds and startup now pass; all four services are healthy, Alembic reports 0011
(head), and worker --status reports no jobs. No live AI requests or emails sent.

Phase 2 remains active: budgeted semantic query retrieval, hybrid evaluation and
page-cited answers are next. Failed/cancelled jobs have no retry UI yet. Live private
storage/scanning setup and worker rollout remain required before enabling indexing.


### Hybrid retrieval baseline (active, 2026-10-19)
Combine existing owner-scoped FTS and vector candidates using deterministic reciprocal
rank fusion, retaining exact page excerpts and suppressing overlapping citations.
Use a caller-provided validated query vector: this increment performs no provider
I/O and exposes no new endpoint before query consent/budgeting exists. Test source
validation, ownership, deterministic ordering and duplicate suppression with fixtures.
No new dependency or migration. Keep semantic accuracy claims deferred until a
representative labelled evaluation; complete backend gates and learning notes.


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


Hybrid increment final validation: Ruff passed; mypy passed for 140 source files;
full backend suite passed 245 tests with one opt-in PostgreSQL skip. That PostgreSQL
integration test passed separately against a disposable local database using actual
FTS and pgvector. Formatting and diff checks passed. Frontend was unchanged, so no
frontend gates were repeated. This internal service is not exposed to students yet.


### Query consent and budget service (active, 2026-10-19)
Add a versioned explicit-consent query schema and a semantic-search service. Reuse
owner-locked daily embedding reservations shared with indexing; commit before any
provider request and retain reservations on failure/cancellation. Require owned,
ready, completed indexing with current disclosure. Keep provider I/O outside DB
transactions, validate its vector and recheck ownership during retrieval. Use fixture
providers only. No new endpoint/UI until this boundary passes tests; no schema or
new dependency required because existing reservations cover embedding usage.


### Consented and budgeted semantic query service (2026-10-19)
Added a bounded question schema requiring explicit acceptance of
paper-query-embeddings-v1. SemanticSearch requires enablement, PostgreSQL, an owned
ready document and completed indexing under the current paper disclosure. Query
embedding usage shares indexing's owner-locked UTC daily ledger. Reservations use
UTF-8 bytes times three provider attempts and commit before network I/O; failures,
invalid responses and cancellation retain the allowance. No question text is saved
or logged by this service. Validated vectors feed hybrid retrieval, which rechecks
ownership and page citations. No new dependency, migration, API route or UI yet.

Focused validation passed: five schema/repository tests and real PostgreSQL
integration with fixture providers covering success, budget exhaustion, ownership,
disabled configuration, timeout, malformed vectors and cancellation. Temporary
integration databases were removed. No live AI calls or student documents used.
Provider transport remains the existing bounded adapter. Budget reservations are
conservative usage units, not an exact billing estimate. Concurrent independent
connection contention and midnight-boundary tests remain before public rollout.
Next: wire an authenticated API and explicit query disclosure in the reader, with
setup-off, quota and provider-error states; then evaluate representative retrieval.


Query-service final gates: 250 backend tests passed with one opt-in PostgreSQL
skip; that integration test passed separately on PostgreSQL with fixture embeddings,
including cancellation and invalid-vector usage retention. Ruff, formatting and
mypy (141 source files) passed. No frontend contracts changed, so frontend gates
were not repeated. Phase 2 remains active; no semantic endpoint deployed yet.


### Semantic query API and reader integration (active)
Expose authenticated POST /documents/{id}/semantic-passages using the tested query
service. Gate on indexing configuration, close provider connections, map provider
errors to safe messages, and retain private response headers. Add an unchecked
query-sharing disclosure to semantic passage search for completed indexes. Preserve
keyword search. Regenerate contracts; test route guards, consent and reader states.


### Semantic search connected to the reader (2026-10-19)
Authenticated POST /documents/{id}/semantic-passages now connects the budgeted query
service to hybrid retrieval. Ownership/readiness and setup are checked before
provider creation; provider connections close on success/failure. Provider failures
return safe retry/keyword guidance without leaking provider details. Responses use
private/no-store headers. Existing quota errors explain the midnight UTC reset.

The prepared-paper reader offers Search by meaning with an unchecked query-sharing
checkbox, bounded question input, loading/error/empty states, source excerpts and
source-page buttons. Consent is local to the mounted form. Keyword search remains
available. This returns related passages, not generated answers or proof of support.
Feature enablement and completed indexing are required; setup remains off by default.
OpenAPI/frontend contracts regenerated. No dependency or database migration added.
Next: representative retrieval evaluation, then grounded answers with page citations.
Live private storage/scanning and indexing worker setup remain prerequisites.


Semantic API/reader validation: backend Ruff and mypy passed (141 files); pytest
250 passed, one opt-in PostgreSQL skip (service integration passed separately in
the previous increment). Frontend lint/typecheck passed; 94 unit tests passed;
generated contract check passed; production build and all 16 Playwright flows
passed, including unchecked consent, zero pre-consent calls, exact request payload,
source-page navigation, accessibility and mobile overflow checks. No live AI calls.

Local deployment: Docker API/web builds passed and compose up --wait completed; all four services healthy. Semantic setup remains disabled by default. No live provider calls made.


### Auditable passage evaluation (active)
Add an offline evaluator for labelled passage rankings: Recall@5/10, MRR, binary
nDCG@10, duplicate rate, exact citation coverage, unsupported-query retrieval rate,
and latency percentiles. Validate input references and compare engines on identical
query sets. Provide synthetic metric sanity fixtures, explicitly not real semantic
quality evidence. No network, private data, dependencies or production behavior change.


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


Evaluation-tooling gates: Ruff passed, mypy passed (142 source files), full backend
suite passed 258 tests with one opt-in PostgreSQL skip. Two further metric edge
cases were added after full-suite collection; the complete focused evaluator suite
passed all 10 tests. CLI execution produced the expected synthetic arithmetic.
Frontend and database behavior were unchanged; no frontend rebuild or deployment
was required. Real-paper evaluation is still pending, not claimed complete.


### Public-paper pilot benchmark (active)
Start with a small public-paper pilot before the proposed 12-paper corpus. Download
publisher PDFs only for local evaluation, record hashes and source attribution,
label exact page/chunk evidence before inspecting search results, and run the existing
PostgreSQL retriever on an isolated fixture database. Keep labels provisional and
single-agent-reviewed, not human gold labels. No live embedding calls in this step.
Record measured FTS results and limitations; semantic/hybrid quality remains pending.


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


Public-pilot final validation: actual PostgreSQL pilot completed (six queries, no
failed requests); temporary database removed. Ruff/mypy passed. Full backend suite:
262 passed, one opt-in PostgreSQL skip. Focused pilot/evaluator tests: 12 passed.
A separate focused invocation initially hit a Windows default pytest temp-directory
permission error; rerunning with a project-local --basetemp passed. No production
behavior, API, schema or frontend change; no app rebuild required this increment.


### Broader public-paper pilot (active)
Add a second compact public paper and freeze evidence labels before running FTS.
Verify PDF and extracted-page hashes, retain raw rankings, and aggregate equal query
sets without identifier collisions. Current server has no embedding API key; do not
substitute fake vectors or claim semantic comparisons. Record the setup dependency.


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


Two-paper final gates: Ruff and mypy passed; full backend suite 264 passed with one
opt-in PostgreSQL skip. Actual second-paper PostgreSQL retrieval completed separately
without failed queries, and its disposable database was removed. Aggregation CLI
exactly reproduces the saved combined report. No frontend/API/schema changes or
live AI requests. Server embedding key remains unconfigured; semantic comparison
is explicitly pending.


### Gemini embedding integration (active, 2026-10-19)
Implement the verified Gemini Embedding 2 REST transport using existing HTTPX,
1536-dimensional normalized vectors and distinct model identity. Bind durable jobs
and query consent to provider-specific disclosure versions; reject stale approvals
and mismatched result models before persistence/retrieval. Keep OpenAI compatibility.
Include task-prefix bytes in conservative quota reservations, renew worker leases
between Gemini single-input requests, and surface provider/privacy disclosures in UI.
Add fixture tests for transport, consent/model isolation and quotas; run backend and
frontend gates and regenerate contracts. Private uploads remain gated by scanner/storage
setup. No private documents or Gmail content in live validation.


### Gemini paper embeddings (2026-10-19)
Added Gemini Embedding 2 using existing HTTPX transport, with fixed HTTPS origin,
1536-dimensional normalized vectors, bounded retries/timeouts/response size, and
no secret-bearing provider errors. One paper chunk per request avoids aggregation;
worker leases renew between requests. Document/query task-prefix bytes count toward
conservative daily usage reservations. No dependency or migration was added.

Provider-specific disclosure versions bind accepted paper jobs and query requests
to Gemini or OpenAI. A provider change requires fresh approval, invalidates old
leases, and rebuilds the index; mismatched result models are rejected and database
retrieval filters by exact model. UI consent names the provider and explains Gemini
free-tier data use. Form consent resets when the provider changes. Existing OpenAI
behavior remains available. Local configuration selects Gemini, but indexing and
private uploads remain disabled pending scanner/storage/worker setup validation.

A live generic-text request through the implemented adapter returned a valid Gemini
vector. No private paper, CV or Gmail content was submitted. PostgreSQL integration
with fixture vectors verified consent isolation, lease replacement, quota accounting
and successful retrieval plus wrong-model rejection; its temporary database was removed.
This is functional validation, not a measured improvement in semantic relevance.
Next: compare Gemini vector/hybrid retrieval against the saved public-paper FTS pilots
with fixed labels, then complete supported-answer checks and private upload setup.


Gemini integration validation: Ruff and mypy passed. Full backend suite: 275 passed,
one opt-in PostgreSQL skip; that PostgreSQL suite passed separately against a
disposable migrated database. The final worker lock-order adjustment passed 18
focused indexing/Gemini tests and the PostgreSQL integration again. Frontend lint,
typecheck, all 96 tests, API contract generation/check and production build passed;
all 16 Playwright flows passed. Generic live Gemini adapter validation passed.
Provider changes now skip busy owner locks during claim to avoid lock-order waits.
The initial OpenAI-specific factory mock and a fixture inheriting local .env provider
settings were corrected; no failing check remains. Phase 2 is still incomplete:
Gemini quality comparison, cited answers and live private upload setup are next.


### Public Gemini comparison (active, 2026-10-20)
Reuse hash-frozen Scikit-learn and LIBLINEAR pilot PDFs and labels. Extend the
benchmark to precompute bounded Gemini document/query embeddings before database
transactions, then compare production FTS, vector and hybrid retrieval on identical
inputs. Record query embedding latency separately from retrieval-only timing; keep
raw rankings, exact-source citation audits and unsupported-query retrieval rates.
Run only public text with explicit CLI opt-in and hard request/input budgets. Stop
on provider errors rather than fill with fake vectors. Test preflight guards and
rerun evaluator/backend gates. Store results and limitations; do not tune production
ranking on this small provisional two-paper corpus. No private uploads or UI changes.


### Live Gemini retrieval pilot (2026-10-20)
Completed a bounded, public-text-only comparison on the frozen Scikit-learn and
LIBLINEAR pilots: eight answerable and four unsupported questions, 28 document
chunks and 12 query embeddings. Gemini vector Recall@5/10 = 1.0 and MRR = 0.875;
keyword Recall@5/10 = 0.875 and MRR = 0.6875; current hybrid Recall@5/10 = 0.875
and MRR = 0.8125. Exact slice coverage = 1.0 and duplicate rate = 0 for each method.
All four unsupported questions returned passages for every method. No generated
answers were evaluated; these are tiny same-domain provisional-label pilot results,
not product-wide accuracy or unsupported-claim measurements.

The missed hybrid evidence was traced to its any-overlap filter: it retains a
neighbouring chunk sharing only 150 characters and drops the vector-top-ranked
chunk containing the answer evidence. No production ranking rule or label changed.
Query embedding p50/p95 were 560.26/623.39 ms, measured separately from retrieval.
Keyword rankings exactly match prior runs; saved combined results reproduce offline.
All temporary database rows were rolled back and the disposable database removed.
No private uploads, CVs or Gmail content were submitted. Private feature flags remain
off. See docs/GEMINI_RETRIEVAL_PILOT.md for timings, source limits and reproduction.

Next: add independent adjacent-chunk regression cases and address loss of distinct
evidence during overlap suppression; evaluate with broader held-out labels before
changing retrieval defaults or making accuracy claims. Continue supported-answer
checks and private upload setup within Phase 2.

Final validation for the 20 October pilot: Ruff and mypy passed; full backend suite
278 passed with one opt-in PostgreSQL test skipped. Both live public-paper benchmark
runs separately exercised production FTS/vector/hybrid on migrated PostgreSQL and
completed successfully; their temporary database was removed. Seventeen focused
evaluator/source/budget tests passed. Offline recomputation exactly matched saved
combined metrics and prior keyword rankings. No frontend or deployment changes.


### Preserve overlapping evidence (2026-10-20)
Suppress only passages fully contained in a selected source interval on the same
page. Partial overlaps retain distinct evidence. Keep fusion weights, source
validation and limits unchanged. Add independent regression tests; replay saved
rankings without provider calls; run checks and update the learning log.


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

Validation: Ruff and mypy passed; eight focused hybrid tests passed. Full backend
suite: 283 passed, one opt-in PostgreSQL skip; the PostgreSQL integration passed
separately after starting the stopped local database. The disposable database was
removed. Offline saved-ranking replay completed without provider calls. Docker API
was rebuilt and all four local services are healthy. No frontend/API contract changes
required a frontend test rerun. Phase 2 remains active; generated answers are pending.


### Cited-answer validation foundation (active, 2026-10-20)
Add bounded answer/quote contracts and versioned generation/support-review prompts.
Build evidence only from owner-checked, ready document pages and exact retrieved
source spans. Resolve model references to server-owned page/offset citations.
Validate all claims and quotes before separate support review; missing/uncertain
support yields no answer claims. Keep operational/provider failures distinct from
insufficient evidence. Add adversarial fixtures for forged quotes, unrelated true
quotes, incomplete reviews, malicious source instructions and cross-account access.
No live generative provider or API/UI exposure yet: consent, durable generation
quotas and provider evaluation must precede enabling answers. No schema/dependency
change; update specification, roadmap and teaching log after validation.


### Cited-answer validation foundation (2026-10-20)
Added strict, bounded answer/claim/quote/review contracts, exact source-span
validation and versioned generation/support-review prompts. Evidence loading checks
account ownership and ready document status. Provider citations identify retrieved
passages; the server resolves page numbers and offsets and rejects fabricated, blank
or out-of-passage quotes before support review.

A separate review must address the question and support every claim. It receives
quotes plus surrounding retrieved excerpts to check omitted qualifications. Any
unsupported or uncertain verdict withholds all claims. Empty context or provider
abstention produces insufficient_evidence; malformed responses, missing review,
timeouts and provider failures produce unavailable instead. Cancellation propagates.
No-answer responses never contain the rejected generated claims. A 60-second total
deadline and 32 KiB response validation limit bound the provider interface.

This is a tested orchestration foundation with fixture providers, not a live answer
feature or measured entailment accuracy. Exact citation integrity is deterministic;
semantic support still depends on the future reviewer and must be evaluated. Prompt
data separation is tested, not a guarantee of model resistance to source instructions.
No generative requests, private data sharing, migrations, dependencies or API/UI
changes were made. Existing retrieval behavior and private feature flags are unchanged.

Next: implement the bounded generative provider adapter and evaluate both generation
and review on public supported/unsupported examples. Add provider-specific consent,
durable generation usage reservations and owner rechecks before any live endpoint/UI.

Final validation: Ruff and mypy passed; full backend suite 309 passed with one
opt-in PostgreSQL skip. All 26 focused answer tests passed after the final reviewer
context change. Tests use fixture model outputs; no live generation occurred.
The new modules are not wired to an endpoint, so no app rebuild or frontend test
rerun was needed. Source and test changes were reviewed; Phase 2 remains active.


### Gemini answer adapter and public evaluation (active, 2026-10-20)
Add fixed-origin Gemini 2.5 Flash-Lite REST generation/review using existing HTTPX
and strict response validation. Bound request/response sizes, output tokens and
time; use no automatic retries, tools or redirects. Run transport fixtures before
public-text-only live checks. Evaluate the frozen public supported/unsupported
questions with saved retrieval rankings; record unavailable outcomes separately
from abstentions. No private student data or app endpoint exposure. Generation
consent, durable quotas and UI remain a subsequent integration requirement.


### Gemini answer transport increment (2026-10-20)
Implemented `apps/api/app/documents/gemini_answers.py` using the existing HTTPX
client, with fixed Google origin, secret header, bounded input/output, structured
JSON, timeout, no redirects/tools/automatic retries, and safe error codes. The
answer pipeline generates claims, validates exact quotations, then independently
reviews support. Opaque thought signatures are accepted as bounded metadata and
never forwarded to answers. No dependency was added.

Live smoke checks: Gemini 2.5 Flash-Lite returned HTTP 404 for this key; the model
listing exposed Gemini 3.1 Flash-Lite, which is now explicitly selected. A public
scikit-learn abstract excerpt produced a supported Python-language answer through
both calls; a question asking for a personal phone number abstained. These two
manual smoke checks are NOT the frozen 12-question benchmark, an accuracy result,
or proof of injection resistance. Their page/offset context was constructed for
transport testing, not loaded from stored PDF pages. No private data was sent.

Validation: 15 transport fixtures pass, covering request isolation, malformed and
truncated responses, model mismatch, tools, bounds, rate limits, redirects,
timeouts, cancellation and metadata. Full backend suite: 324 passed, one opt-in
PostgreSQL test skipped. Ruff and mypy pass after formatting. The final metadata
adjustment was covered by the focused suite and type checking.

The adapter remains unexposed in app routes. Next: run and manually audit the
frozen public-paper answer benchmark, then integrate explicit generation consent,
durable per-user quotas and owner checks before enabling reading-workspace answers.

### Frozen answer pilot (active)
Build an opt-in public-only runner with hash-checked PDFs, saved rankings, top-five production fusion, bounded 24 calls, incremental results, and separate unavailable outcomes. Run once and audit returned claims against source excerpts; report provisional labels and no held-out accuracy claim.


### Frozen answer pilot runner (2026-10-20)
Added scripts/run_answer_pilot.py and tests/test_answer_pilot.py. Hash-checked
public PDFs and saved rankings feed production fusion and answer validation.
Results are incremental, cannot overwrite earlier runs, and stop on unavailable.
Added safe per-stage diagnostics after two incomplete live runs; no automatic
retries. v1 failed on question one; v2 answered question one with a supported
page-three quote, then failed on question two. Neither run reached unsupported
questions; no accuracy or abstention claim is justified. Full details and raw
artifact paths: docs/PUBLIC_ANSWER_PILOT.md.
Validation: 43 focused tests passed; Ruff passed; mypy app passed (147 files).
No production API/UI, dependencies, schema or private-data behavior changed.
Next: diagnose one bounded unavailable result with the new stage diagnostics,
then finish the frozen evaluation before consent/quota/UI integration.

### Quote fidelity diagnosis (2026-10-21)
The bounded diagnostic reproduced invalid_provider_output after valid generation. A captured public candidate changes ligatures/whitespace in quotations. Strengthen the versioned prompt to preserve exact characters; retain strict validation, test regression, and run a separately recorded pilot. Earlier unavailable failures remain unattributed.

Prompt v2 still fails quote fidelity. Implement bounded deterministic alignment for only PDF ligatures and whitespace, requiring a unique match and whole-character boundaries. Always return original text/offsets to the reviewer and UI. Reject ambiguity and all other character changes; test negation/numbers/punctuation and partial-ligature cases.


### Citation typography and diagnostic findings (2026-10-21)
A bounded diagnostic reproduced invalid_provider_output after successful structured
generation, before support review. Captured public quotes changed PDF ligatures
and whitespace. Earlier provider_unavailable failures remain unattributed.
Prompt v2 explicitly requests preservation of source characters. Deterministic
alignment permits only seven PDF ligature expansions and whitespace folding,
requires a unique fallback match with whole-character boundaries, and sends the
original source substring and offsets to support review and the result. No fuzzy
word matching, punctuation repair, number changes or claim relaxation is allowed.
Tests cover ambiguity, partial ligatures, length limits, altered words/numbers,
and exact original text reaching the reviewer. Benchmark invalid answers now
remain failures while later cases run; service failures still stop the run.

Files: app/documents/answers.py, answer_prompts.py, scripts/run_answer_pilot.py,
tests/test_document_answers.py, tests/test_answer_pilot.py (under apps/api).
No dependencies, migrations, UI exposure or private-data transmission added.


Completed public answer pilot v5: 12 questions, 17 calls; 5/8 answerable questions
answered, 3 rejected for invalid citations, 4/4 unsupported questions abstained.
No service failure in this run. Exact source offsets verified for all returned
citations. Agent audit found four fully cited claims and one whose penalty-parameter
qualifier requires a second citation despite being present in retrieved context.
Earlier failed runs are retained. This is not held-out or human-gold accuracy.
Tests: full backend 335 passed / 1 opt-in PostgreSQL skip; final runner 3 passed;
Ruff and mypy passed. See docs/PUBLIC_ANSWER_PILOT.md for measured latencies and
limitations. Next: server-defined citation choices and stricter qualifier support,
then unseen-paper evaluation before production consent/quota/UI integration.

### Server-defined citations (2026-10-21, active)
Add a bounded exact-source citation catalog at the Gemini adapter boundary. Model returns catalog IDs, server reconstructs existing Candidate quotes. Keep orchestration and source validation. Strengthen reviewer instructions about uncited qualifiers, test malformed/unknown choices and exact source preservation, then run the frozen pilot once. No API/UI enablement.


### Server-defined citation choices (2026-10-21)
Added app/documents/citation_choices.py: deterministic overlapping source slices
(maximum 500 characters, stride 350) form a bounded catalog. Gemini returns IDs;
the server reconstructs the existing Candidate schema with original quotations.
Unknown and duplicate IDs fail validation. Existing ownership/context validation,
source-offset resolution and support review remain in place. Generation uses
paper-citation-choices-v1; support review v2 explicitly rejects uncited factual
qualifiers. The public runner records both prompt versions. No new dependencies,
schema migrations or live endpoint/UI were introduced.
Files changed: citation_choices.py, gemini_answers.py, answer_prompts.py,
scripts/run_answer_pilot.py, tests/test_citation_choices.py and transport tests.

Citation-choice validation complete: 341 backend tests pass, one opt-in PostgreSQL
skip; Ruff/mypy pass. Public v6 plus unattempted-case continuation: 7 answers,
4 abstentions, 1 retained timeout across 12 questions; no citation-copy failures.
Exact quote provenance passes, but reviewer still accepts the uncited penalty
qualifier. No general accuracy claim or production enablement. See
PUBLIC_ANSWER_PILOT.md for artifacts and audit limitations. Next: selected-citation
support checking, explicit qualifier regression and unseen-paper evaluation.

### Isolated support and context reviews (2026-10-21)
First review only selected quotes and claims for complete factual support. Only after passing, review surrounding excerpts for contradictions/omitted qualifications. Both must pass; retain total 60-second bound. Add fixture regressions and bounded live public qualifier checks. Maximum full pilot becomes 36 calls; no production enablement.


### Isolated support and context gates (2026-10-21)
Changed answers.py so the first review receives only the question, claims and their
selected citations. After support passes, a separate context-veto review receives
retrieved excerpts to detect contradictions or omitted qualifications. Either
negative, uncertain, malformed or failed review prevents an answer. Both stages
remain inside the original 60-second total deadline; each transport retains its
existing timeout. Maximum successful question cost is now three provider calls;
a complete 12-question pilot can use up to 36. No automatic retry was added.

Prompts: support v3 and context v1. The pilot records both versions. Fixture tests
prove uncited excerpts are excluded from the support payload and a failed support
review short-circuits context review; a context veto still suppresses the answer.
Files: apps/api/app/documents/answers.py, answer_prompts.py,
apps/api/scripts/run_answer_pilot.py, apps/api/tests/test_document_answers.py.

Live public regression: reviewer v3 still marked the previously uncited 'penalty'
qualifier supported, and also supported the version with that qualifier removed.
Evidence: apps/api/evaluation/isolated-support-review-v1.json. This is one negative
and one positive diagnostic, not an accuracy benchmark. Isolation did not solve
this semantic-review failure. Keep this negative example as a regression case;
do not treat model review as a guarantee or enable the answer UI on this evidence.
Next: compare a different review strategy/model against frozen positive/negative
support labels, then use unseen papers to assess generalization. Production
consent, durable quotas and owner rechecks still remain outstanding.

Validation for isolated-review increment: 343 backend tests passed, one optional PostgreSQL test skipped; 60 focused tests passed; Ruff and mypy passed (148 files). Live qualifier negative regression failed as documented; UI remains disabled.

### Frozen support-review comparison (2026-10-21)
Create eight synthetic labelled examples (four supported, four unsupported) before calls. Compare current quote-only prompt with a conservative literal-support prompt using the same bounded provider. Save all outcomes, count unavailability separately, no retries or production prompt changes based on a single run. Test scoring; document limits and make a concrete next-step decision.

### Generation consent/reservation foundation (2026-10-21)
Reviewer comparison stopped on first unavailable result; preserve it without accuracy claims. Independently add owner-scoped generation reservations with current consent version/model, UTC day and three-call allowance. Additive migration; deletion of a document cannot reset daily use. Caller must commit before network I/O; no endpoint/UI yet. Test ownership, duplicate IDs, quota persistence and consent validation. PostgreSQL concurrency remains an explicit validation requirement.


### Generation consent/reservation foundation (2026-10-21)
Added AnswerReservation model and additive migration 20261021_0012. A strict
AnswerRequest requires accepted consent and paper-answer-gemini-v1, bounded
question text and request UUID. reserve_answer verifies ready owner-scoped pages,
locks the owner row, rejects reused request IDs and reserves three provider calls
against a UTC daily allowance. It records disclosure/model/acceptance time but
never question text. Document deletion cannot reset usage; account deletion
cascades the reservation. Caller must commit before network I/O; failed calls keep
the reservation. This is a call-count allowance, not measured token cost. Existing
transport input/output caps still bound each call.

Files: apps/api/app/db/models/answer_usage.py, models/__init__.py,
apps/api/app/documents/answer_usage.py,
apps/api/alembic/versions/20261021_0012_answer_reservations.py,
apps/api/tests/test_answer_usage.py. No endpoint/UI or feature flag was enabled.
Migration was exercised on disposable SQLite fixtures, not applied to the user's
running database. PostgreSQL concurrency validation could not run: Docker's Linux
engine pipe was unavailable. SQLite tests do not prove PostgreSQL locking behavior.

The eight-case synthetic reviewer comparison fixture and script were also added
(evaluation/support-review-cases-v1.json, scripts/evaluate_support_review.py,
tests/test_support_review_evaluation.py). The live comparison stopped on its first
unavailable response; no comparative accuracy conclusion is justified. Failed
result retained in evaluation/support-review-comparison-v1.json. No provider retry.

Next: validate concurrent reservations on PostgreSQL when Docker is available,
then integrate reservation commit and owner recheck around answer execution.
The model reviewer limitation stays open; public answer UI remains disabled.

Validation: full backend suite 348 passed, one opt-in PostgreSQL skip. Final explicit-boolean consent hardening then passed all 6 focused reservation tests; numeric 1 and string true are rejected. Ruff and mypy passed (150 files). No PostgreSQL concurrency result is claimed.

### Guarded answer execution (2026-10-21)
Implement an unexposed service with disabled default, server-side retrieval, exact owner-checked evidence, committed usage before provider I/O, and post-call owner/source revalidation. Retain reservations on failure/cancellation. Require PostgreSQL by default; SQLite only explicit test override. Test reservation visibility, ownership deletion during calls, empty retrieval, disabled mode, duplicate requests and provider failures. Docker remains unavailable; no live migration or concurrency claim.


### Guarded answer execution service (2026-10-21)
Added apps/api/app/documents/answer_service.py and tests/test_answer_service.py.
PaperAnswers is disabled by default and requires PostgreSQL by default. It checks
owner/ready access, retrieves at most five passages server-side, validates their
source text, commits the three-call reservation, closes the DB session, executes
the answer pipeline, then rechecks owner access and source slices before returning.
No network call holds the owner lock. Failures/cancellation retain reserved usage;
reused request IDs cannot trigger another call. Empty retrieval consumes no quota.
Changed sources return 409, deleted/inaccessible documents 404. The service accepts
no caller-supplied excerpts. No route, feature flag or UI enables it yet.

Current retrieval in this service is keyword/FTS (SQLite lexical fallback is only
used in tests via explicit require_postgres=False). Integrating separately consented
semantic retrieval is still pending; this change does not claim hybrid execution.
No new dependency or schema change beyond the previous reservation migration.
Seven fixture integration tests cover successful reviewed output, abstention,
provider failure, cancellation, deletion, source modification, disabled/PostgreSQL
guards, wrong owner, empty retrieval, durable reservation visibility and duplicates.

Docker's Linux engine is still unavailable, so PostgreSQL concurrent quota testing
remains pending. No migration was applied to a live database. The existing semantic
review weakness is unchanged; generated answers remain unavailable in the UI.
Next: PostgreSQL migration/concurrency checks, then an explicitly gated API contract
and provider disclosure before reading-workspace integration.

### PostgreSQL reservation concurrency (2026-10-22)
Start installed Docker if available, test migration in generated disposable database only. Add independent-session race tests: last quota slot allows one request; duplicate request IDs allow one reservation. Clean up generated fixture owners/papers and drop only generated test DB. Recover interrupted full-suite result by rerunning if unavailable. No live schema mutation.


### PostgreSQL quota validation completed (2026-10-22)
Started installed Docker Desktop in the background and the existing PostgreSQL
service. Created a uniquely named disposable database, migrated it to head, ran
two independent-session reservation races and the existing PostgreSQL retrieval
integration test: all three passed. With one quota slot left, exactly one request
reserves usage; with the same request ID, exactly one succeeds and the other gets
answer_request_used. The test uses separate connections, not nested savepoints.
The 0012 reservation migration also passed downgrade-to-0011 and re-upgrade.
Only the disposable database was dropped; the user's application database schema
and contents were not changed. Docker and PostgreSQL are left running.

Added apps/api/tests/test_answer_usage_postgres.py. Run with
TEST_DOCUMENT_POSTGRES_URL pointing to a migrated disposable PostgreSQL database:
uv run pytest tests/test_answer_usage_postgres.py tests/test_document_retrieval_postgres.py.
Do not point integration tests at a production database. No new dependencies.

The interrupted guarded-service suite had no recoverable process result, so the
full backend gate is being rerun. UI and answer enablement remain unchanged.
Next: gated answer API status/disclosure and request contracts, including HTTP
consent validation, while keeping the feature disabled until remaining evaluation
and reading-workspace integration are ready.

Final validation (2026-10-22): full backend 357 passed; 3 opt-in PostgreSQL cases skipped in that default run and all 3 passed separately against the disposable PostgreSQL database. Ruff and mypy passed (151 files). Migration downgrade/re-upgrade passed and disposable database removal confirmed.

### Disabled-by-default answer API (2026-10-22)
Add owner-scoped status/disclosure and reviewed-answer POST, feature/key/PostgreSQL gates, JSON UUID parsing with strict consent, provider cleanup and private response headers. Test transport boundaries with fixtures and regenerate typed contracts. Do not enable local generation or add UI yet.


### Gated answer API contracts (2026-10-22)
Added GET /api/v1/documents/{document_id}/answers for owner-scoped provider/model,
consent disclosure, reserved calls today and daily allowance. Added POST on the
same path for a validated question, request UUID and explicit current consent.
Generation requires DOCUMENT_ANSWERS_ENABLED, a Gemini key and PostgreSQL; default
is false. Daily call limit defaults to 30 (three reserved per question). Neither
local .env nor running containers were changed or enabled.

The route checks ready ownership before constructing the provider, commits the
request transaction before calling the guarded service, and always closes the
provider. It uses existing private/no-store responses. UUID strings are accepted
at the HTTP boundary while accepted remains strictly boolean true; old disclosure,
blank questions and malformed UUIDs fail validation. API tests cover disabled mode,
cross-account/anonymous access, valid JSON UUID, strict consent, private success
headers and cleanup on success/quota error using fixtures, not live model calls.

Files: apps/api/app/api/v1/routes/documents.py, app/core/config.py,
app/documents/answer_usage.py, .env.example, tests/test_answer_api.py, openapi.json;
apps/web/src/lib/api/generated contracts regenerated. No database migration or
new dependency was needed. No reading UI change or generated-answer release yet.
Next: reading-workspace disclosure/status integration and disabled/loading/error
states; retain explicit consent and reset it when disclosure changes. Reviewer
limitations and unseen-paper evaluation remain release concerns.

Answer API validation: 358 backend tests passed; 3 opt-in PostgreSQL tests skipped in this run (passed separately in prior increment). Ruff/mypy passed. Frontend lint, typecheck, 96 tests, production build and generated API consistency check passed. Next.js emitted the existing multiple-lockfile workspace-root warning; build succeeded. No live provider calls, database migration or feature enablement occurred.

### Reading-workspace answer UI (2026-10-22)
Add runtime-validated API helpers and a status-driven answer panel in extracted pages. Consent unchecked and reset on document/provider/model/disclosure changes. Explicit submission only, unique request IDs, no automatic mutation retries, quota/loading/error/abstention states, safe text and clickable source pages. Keep backend feature disabled. Test UI boundaries and existing flows.


### Reading-workspace answer UI completed (2026-10-22)
The extracted-page workspace now includes a status-driven Ask about this paper panel.
Runtime-validated API responses drive disabled, loading, quota, error, abstention and
cited-answer states. Sharing consent starts unchecked and resets when the document,
provider, model or disclosure changes. Explicit submissions use unique request IDs,
a synchronous duplicate-click guard and no automatic retries. Source quotes render
as text; citation buttons select and focus the corresponding extracted page.
Frontend lint/typecheck and all 104 unit tests passed. The production build and all
16 Playwright flows passed, including consent, citation navigation, accessibility
and mobile layout. Browser answers used fixtures; no live AI calls were made.
No dependency or database change. Generated answers remain disabled locally, and
these source changes have not been deployed to the running Docker application.
Next: complete the remaining reading-workspace integration and evaluate citation
support on unseen papers before enabling generated answers. Gmail remains a later phase.


### Connected PDF reading layout (2026-10-22)
Integrate the existing private PDF viewer beside extracted text and questions on wide screens, stacked on mobile. Opt-in opening preserves bandwidth; citations pass the selected page to the browser PDF viewer. Keep extracted text as a fallback because native PDF support varies. Test page URL changes, cleanup, existing browser flows and frontend gates. No dependency or backend changes.


### Connected original-PDF reader (2026-10-22)
The extracted-page workspace can show the private original PDF beside questions
at wide desktop sizes, with a stacked mobile layout. Citation and passage page
selection also requests the matching native PDF page. Opening is explicit; page
changes reuse the cached private file and revoke replaced object URLs. Extracted
text remains available when browser PDF support or storage is unavailable.
No new dependency or backend/schema change. Generated answers remain disabled;
source changes are not yet rebuilt into the user's Docker application.
Next: persist owner-scoped reading conversations and continue unseen-paper support
evaluation before enabling live answers. Native PDF page fragments are browser
requests, not a guarantee that every PDF plugin navigates successfully.

Validation: frontend lint/typecheck passed; 105 unit tests passed; production build and all 16 Playwright flows passed, including split-reader failure fallback, accessibility and mobile overflow checks. PDF page fragment/reuse/cleanup checks use a Blob fixture, not a real browser PDF plugin. Existing Next.js workspace-root and standalone warnings remain. Git diff whitespace check passed.


### Private reading history execution plan (2026-10-22)
Persist completed questions and validated answer/abstention snapshots with request ID, model and disclosure metadata. Cascade on document/account deletion. Add an owner-checked bounded history endpoint; show latest 20 entries independently of generation availability and refresh after explicit asks. Preserve duplicate-request rejection, recheck source access before saving, and never feed history to the model. Test persistence, cross-owner denial, cascades, no-save on cancellation/source changes, contracts and UI. Add migration; validate on disposable databases only.
