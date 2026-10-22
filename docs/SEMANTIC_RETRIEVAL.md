# Semantic retrieval implementation status

## Implemented foundation

`app/documents/embeddings.py` wraps the existing async HTTPX dependency. The chosen
baseline is `text-embedding-3-small` with 1536 dimensions, not a measured winner.
The API shape and dimension option follow the official documentation:
https://developers.openai.com/api/reference/resources/embeddings/methods/create

A maximum of 32 text passages, each at most 1200 characters, is accepted per call.
This is a conservative bound for existing page chunks, not tokenizer measurement.
Only the configured official OpenAI origin is accepted outside test environments;
redirects and environment proxies are disabled. Response bodies are bounded to
4 MiB. There are at most three attempts within 65 seconds. A long Retry-After is
returned to the caller as deferred work rather than retried prematurely.

Response validation checks model, vector dimensions, input indices, finite/nonzero
values and usage consistency. Vectors are normalized and reordered by input index.
Errors contain stable codes, not paper contents, provider bodies or credentials.
Callers must close the adapter with `aclose()` and reserve usage before requests.

## Not enabled

No routes or worker call this adapter. Existing PDFs and keyword search do not
trigger embedding requests. There is no vector table, vector-search quality result,
AI usage ledger or cited answer generator yet. No live API calls were made.

Before enabling: add account-owned pgvector storage tied to document/page offsets,
model and content hash; durable jobs and quota reservations; disclosure that paper
text is sent to the AI provider; deletion and reindex checks. CVs and Gmail contents
must stay outside this path. Keep keyword search working during provider outages.

## Testing and troubleshooting

Run `uv run pytest tests/test_embeddings.py -q` from apps/api. Fixtures cover
response order, normalization, input bounds, malformed vectors, mismatched models,
retry limits, rate-limit deferral, oversized responses, transport recovery and
cancellation. They measure adapter correctness, not semantic retrieval quality.

`embeddings_not_configured`: no server-side API key. Do not paste keys into chat.
`invalid_embedding_response`: reject the entire batch; do not store partial vectors.
`embedding_provider_unavailable`: worker should respect retry_after and bounded jobs.
Never log provider errors or input text while debugging.


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


## Consent interface and worker operation (2026-10-17)
The reader now offers version-bound consent only when indexing is configured.
It explicitly explains that extracted paper text goes to OpenAI; the checkbox is
unchecked. Authenticated GET/POST/DELETE /documents/{id}/index expose status, enqueue
and cancellation. Repeated enqueue returns the same job. Failed/cancelled jobs do
not yet have a retry button. Cancellation fences further batches, not an already
in-flight provider request, and does not refund conservative reserved usage.

Settings (server-side): DOCUMENT_INDEXING_ENABLED=false by default;
DOCUMENT_EMBEDDING_DAILY_LIMIT=1000000 conservative token units per account/UTC day.
An OpenAI key and PostgreSQL are required. Enable only after the scanning/storage
setup and worker are validated. The flag does not prove worker health.

After migrations, from apps/api:

    uv run python -m app.documents.index_worker --status
    uv run python -m app.documents.index_worker --once
    uv run python -m app.documents.index_worker

--status reports aggregate counts without calling AI. --once processes at most one
job. The loop requires explicit enablement and PostgreSQL and closes provider/DB
resources on exit. No default Compose service starts it. Container invocation:

    docker compose run --rm --no-deps api python -m app.documents.index_worker

Keep the feature disabled while hybrid query retrieval and real provider evaluation
are pending. The current interface prepares vectors; it does not offer AI answers.


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


## Gemini provider (2026-10-19)
Set server-only `DOCUMENT_EMBEDDING_PROVIDER=gemini` and `GEMINI_API_KEY` in
`apps/api/.env`. Keep `DOCUMENT_INDEXING_ENABLED=false` until private Storage,
scanner, PDF processing and a continuous indexing worker have been validated.
The key alone does not enable uploads, indexing or generated answers. Recreate
Docker services after configuration changes. Never put the key in NEXT_PUBLIC variables.

The existing worker command (`python -m app.documents.index_worker`) now selects
the configured provider. Gemini Embedding 2 uses one input per request, a 1536-value
normalized vector, document/query task prefixes and fixed Google HTTPS origin.
The transport shares existing bounded retries/timeouts and redacted error codes.
No SDK/dependency or database migration is needed. Gemini returns no usage total
on this endpoint: prompt_tokens=0 means unavailable, not a zero-cost request; quota
accounting reserves UTF-8 input bytes including task prefixes, times three attempts.

Gemini consent versions are `paper-gemini-v1` and `paper-query-gemini-v1`. Existing
OpenAI approval never permits Gemini processing. Changing providers requires new
student approval, invalidates the prior job lease, and queues replacement indexing.
Old vectors remain until atomic successful replacement; searches require a completed
job for the approved provider and filter vectors by exact model. A worker only claims
jobs for its own provider. Old workers should be stopped when changing configuration.

Consent screens identify Google Gemini and explain free-tier product-improvement
use. Use public papers and nonprivate questions on free tier. CVs and Gmail replies
are not part of this pipeline. API key storage is server-only. Outreach generation
still uses its existing provider/template; this change only concerns semantic search.

Official references: https://ai.google.dev/gemini-api/docs/embeddings and
https://ai.google.dev/gemini-api/docs/pricing . Provider pricing/terms should be
reviewed again before public launch. Semantic retrieval quality remains unmeasured
with Gemini; passing transport tests does not establish relevance accuracy.
