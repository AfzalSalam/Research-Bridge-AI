# ROADMAP.md

Implement and review one phase at a time. Every phase requires an active plan,
the applicable quality gates, a learning-log entry, and a clear commit after
acceptance.

## Phase 0 — Audit and plan

Audit the repository and Figma prototype, decide what can be reused, establish
the architecture and product boundaries, and create the first execution plan.

**Status:** Approved and complete.

## Phase 1 — Foundation

Create the Next.js TypeScript frontend, FastAPI backend managed by uv, local
PostgreSQL with pgvector available for later use, versioned health endpoint,
typed frontend health display, environment examples, reproducible toolchain,
tests, linting, type checking, builds, and Windows-friendly documentation.

Do not implement business features.

**Status:** Complete.

## Phase 2 — Design system and responsive shell

Translate the approved Figma direction into project-owned tokens, typography,
accessible shadcn/ui-based primitives, responsive navigation, route shells,
data-state patterns, and a component gallery. Fix the mobile navigation and
overflow problems found during the Figma audit.

**Status:** Complete.

## Phase 3 — Typed mock product journey

Build the complete placement demo with typed fixtures: profile, topic search,
honest progress, mentor results, master-detail evidence, custom editable draft,
internships, saved items, application tracker, demo labels, responsive states,
and a Playwright critical flow.

No real academic APIs, AI, authentication, or database persistence.

**Status:** Complete.

## Phase 4 — Backend contracts

Add modular FastAPI routers, configuration, structured errors, request IDs,
logging, versioned request/response schemas, service interfaces, mock services,
OpenAPI export, and a generated or contract-checked TypeScript API client.
Replace frontend fixture access with the mock backend without changing behavior.

**Status:** Complete.

## Phase 5 — Database and profile

Add SQLAlchemy 2, Alembic, profiles, interests, skills, projects, preferences,
papers, authors, institutions, provenance, saved items, drafts, applications,
and application events. Implement repositories, ownership-ready fields,
constraints, indexes, migrations, and profile integration.

**Status:** Complete.

## Phase 6 — OpenAlex discovery and normalization

Integrate OpenAlex as the first real source with async HTTPX, typed models,
timeouts, bounded retries, rate-limit handling, caching interfaces, partial
failures, provenance, normalization, deduplication, author/institution
resolution, and representative fixtures.

Other academic providers remain honest interfaces until implemented.

**Status:** Complete.

## Phase 7 — Basic relevance and evidence

Derive mentor candidates from supporting-paper authors. Implement the
placement-release deterministic heuristic, configurable weights, feature
contributions, evidence completeness, uncertainty, source links, and tests.
Measure retrieval success, duplicate rate, evidence coverage, unsupported-claim
rate, and latency without claiming research-grade ranking quality.

**Status:** Complete.

## Phase 8 — Evidence-grounded outreach

Generate only after mentor and paper selection. Add versioned prompts,
structured outputs, claim-to-evidence mapping, editable draft versions,
uncertainty warnings, provider metadata, deterministic fallback templates, and
failure/grounding tests. Never send email automatically.

**Status:** Complete.

## Phase 9 — Internships and application tracker

Implement verified opportunity ingestion, allowlisted controlled extraction
only where needed, funding/work-mode `Unclear` states, source and last-verified
metadata, stale/expired detection, saving, application status history, notes,
and follow-up dates.

**Status:** Complete.

## Phase 10 — Authentication, privacy, and security

Compare and select authentication, then implement protected routes, backend
token validation, user isolation, private object storage, upload controls, rate
limits, safe rendering, SSRF protection, extraction allowlists, audit-relevant
events, deletion, security tests, and a threat model.

## Phase 11 — LangGraph workflow and progress

Orchestrate the already-tested services with typed state, honest progress,
recoverable errors, cancellation, persistence/checkpointing, SSE updates, and
human pauses for mentor selection and draft review. Deterministic logic remains
outside the LLM and independently testable.

## Phase 12 — Quality and observability

Complete unit, integration, database, contract, E2E, accessibility, security,
and failure tests. Add structured logs, request/search IDs, privacy-safe model
metadata, tracing interfaces, and reports for retrieval success, duplicate
rate, evidence coverage, unsupported claims, and latency.

## Phase 13 — Deployment and portfolio release

Deploy Next.js, FastAPI, PostgreSQL, and private object storage with CI/CD,
secrets, migrations, backups, health/readiness checks, preview/staging flow,
smoke tests, rollback and incident runbooks. Add deterministic demo mode,
architecture diagrams, screenshots, a polished README, limitations, and a
short recruiter interview demo script.

### Placement release gate

The placement release is complete only when the live and demo critical journeys
work, evidence claims are supportable, mobile and accessibility checks pass,
quality reports contain actual results, and deployment/rollback documentation
has been exercised.

## Phase 14 — Post-placement ranking and enrichment research

After the placement release, evaluate PostgreSQL full-text retrieval, pgvector,
embedding strategies, weight tuning, labelled relevance sets, cross-encoder
reranking, Recall@5/10, MRR, nDCG@10, and larger-scale multi-source enrichment.
Adopt complexity only when measurements show a benefit.

## Phase 15 - SaaS Foundations & Real Authentication

**Status (2026-10-07):** Account-profile and guided-workflow isolation slice
implemented. Onboarding, profile edits, mentor inputs, and workflow access now
share the authenticated owner. Automated checks use isolated identities and
provider fixtures; live Supabase/PostgreSQL verification and the wider privacy
audit remain open. See `docs/plans/phase-15-saas-foundations.md`.

Transition the architecture from a recruiter demo to a multi-tenant application.
Enforce strict JWT verification in deployed environments; isolate test identities
to explicitly configured test environments.
Integrate a live authentication provider (e.g., Supabase), create robust user
onboarding flows to capture initial profile data, and definitively audit all
SQLAlchemy repositories to ensure 100% data isolation based on owner_id.

## Phase 16 - SaaS UX Refresh & Landing Page

Convert the portfolio-oriented frontend into a professional SaaS product.
Design and implement a conversion-optimized landing page, simplified student
dashboards, intuitive onboarding screens, and highly polished UI components. 
UI changes should be extremely professional, easy for beginners to understand, 
and follow the strict accessibility and motion rules established in earlier phases.


## Approved addition — Direct university website discovery

Implemented 2026-10-09: a separate authenticated website scan on Discover with
10/20/30-paper targets, streamed partial results, reviewed official sources,
provenance timestamps, explicit internship work-mode evidence and filtering.
See `docs/plans/university-website-discovery.md`. This addition does not complete
future ranking evaluation, durable background jobs, professor availability
verification, or saving website results into the outreach workflow.


## Approved student research workspace (2026-10-10)

Implemented tab-local, account-scoped discovery persistence; navigation-safe
searches; simpler Discover / Find Professors copy; grouping of returned authors
by shared paper; automatic region-filtered selection across seven reviewed
university sources; and elapsed/count/budget scan progress. Browser refresh
interrupts unfinished work while restoring received evidence. This does not add
all-university coverage, durable jobs, cross-device search history or confirmed
professor roles/vacancies. See docs/plans/student-research-workspace.md.


## Approved public email and worldwide discovery extension (2026-10-10)
Public-email lookup uses a stored author identity, official profile name and
matching ORCID/publication evidence. Published addresses retain source, check date
and identity evidence; ambiguous profiles stay review links. No guessed addresses,
deliverability promises or automatic sending. A selected author can supply an
optional official profile URL. Public lookup evidence is cached in PostgreSQL.

The seven reviewed starting sources are supplemented by institutions found in
relevant OpenAlex paper affiliations and verified through ROR v2. A website scan
selects up to six additional institutions, with regional filtering and a shared
120-second crawl/preparation budget. Contact lookup resolves up to six author
institution records and has a 90-second budget. Registry provenance is displayed.
Institution membership does not prove an open internship or professor availability.
This is bounded worldwide discovery, not exhaustive global coverage.


## Research-to-conversation extension

Active execution plan: docs/plans/research-to-conversation.md.
Connected workspace implemented and deployed locally; 14 browser tests and the
PostgreSQL migration/ownership smoke check pass. ArXiv-only citation resolution
now uses canonical DOI matching with explicit unresolved states. Next phases: private cited PDF reading, Gmail
reviewed sending, synchronized conversations, then public-release verification.
Google Cloud has not been configured by the owner; docs/GMAIL_SETUP.md provides
preparation steps. No live Gmail behavior has been tested or advertised.


### Early contact availability (2026-10-11)
Discover now starts a first pass of public-email checks alongside academic paper
results: up to six distinct authors, two concurrent lookups, corresponding authors
prioritized within each paper and checks spread across papers. Source-backed
addresses and exact-author Contact links appear on paper cards. A contactable-only
filter is optional; unverified, failed and unchecked states are explicit. Broader
visual redesign is deferred until the core journey works. Frontend static checks,
68 unit tests and 15 browser tests pass.


### Private PDF reading progress (2026-10-12)
Ingestion primitives implemented and tested: fail-closed antivirus protocol,
isolated bounded extraction, 20 MiB/100-page limits, explicit unsupported states,
numbered text pages and exact chunk offsets. No upload feature is exposed yet.
Owner-scoped document/page records and durable job leasing are now implemented.
Private storage, worker orchestration, reading UI and retrieval/Q&A remain pending. See docs/PRIVATE_PDF_SETUP.md for preparation and limitations.


PDF persistence increment: additive migration 20261012_0007, atomic enqueue,
five-minute fenced leases, three-attempt limit, delayed transient retries, terminal
unsupported states and ready-only page reads. Backend gates pass (174 tests).
Local PostgreSQL verified SKIP LOCKED, expired-lease recovery and stale completion
rejection; Docker is healthy. No upload API is enabled yet.


### Private PDF storage and worker increment (2026-10-15)
Implemented private Supabase transport, UUID-only storage paths, durable upload
intent, 100-document/200-MiB owner quotas, hash checks, scanner/parser worker and
independent file cleanup. Migration 20261012_0008 retains cleanup work after account
deletion; physical deletion is asynchronous and requires a running worker. Upload
API/reader UI and cited retrieval remain pending. No new dependency was added.
Backend: 194 tests passed, Ruff and mypy clean. Storage transport and scanning use
fixtures in automated tests; live private bucket/antivirus verification is pending.
Configuration and worker commands are in docs/PRIVATE_PDF_SETUP.md.


### Private document interface (2026-10-15)
Authenticated upload/list/status/delete and ready-only extracted-page endpoints
are implemented, with private response caching, streamed 20-MiB limits and five
persisted upload attempts per owner/minute. The paper workspace has upload controls,
processing states, removal and a safe numbered text preview. Uploads are explicitly
disabled by default pending live Storage/scanner/worker validation. Original PDF
layout viewing, open-access fetching and cited retrieval/Q&A remain pending.
No new dependencies or schema migration were needed for this increment.


### Original PDF access (2026-10-15)
Added authenticated GET /documents/{id}/file for ready documents. The service
checks ownership before fetching, SHA-256 against the scanned bytes, and ownership
and readiness again after fetching. Responses use private/no-store caching and
defensive PDF headers. Storage failures return a safe 503; altered files return
409. No migration or dependency added. Original-reader UI integration, open-access
fetching and cited retrieval remain pending; uploads remain disabled by default.


### Original PDF reader integration (2026-10-15)
Ready PDFs now offer an explicit original-file viewer and download fallback alongside
extracted text. Bearer-authenticated fetch uses no-store; temporary blob URLs are
revoked on close/unmount, pending fetches abort, and query bytes expire immediately
after the reader unmounts. Account identity changes already remount the private
workspace. No dependency or migration added. Browser-native PDF support varies;
the sandboxed preview may require using the download fallback. Live uploads remain
disabled pending Storage/ClamAV validation. Cited Q&A and OA fetching remain pending.


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


### Verified PostgreSQL retrieval and passage-search UI
PostgreSQL integration passed on a freshly migrated temporary database, including
GIN index presence, ready-state/ownership checks, exact page slices, all three
expected first-page matches and three no-match queries. Test database removed.
These remain tiny synthetic smoke tests, not general retrieval accuracy claims.
The extracted-text reader now offers keyword passage search, loading/error/no-match
states and keyboard-accessible source-page buttons. Excerpts remain plain text;
no AI answer is implied. No dependency or schema change beyond migration 0009.


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
