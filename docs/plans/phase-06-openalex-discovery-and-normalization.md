# Phase 06 — OpenAlex discovery and normalization

**Status:** Complete

**Prepared:** 2026-08-01

**Completed:** 2026-08-01

**Scope:** Add the first real academic source as a typed, bounded,
provenance-preserving paper-discovery slice. Persist normalized OpenAlex works,
authors, institutions, authorship affiliations, topics, and provenance while
keeping professor derivation, relevance heuristics, LLM behavior, and other
providers outside this phase.

## 1. Outcome

At the end of this phase:

1. a student can search OpenAlex by a focused text query, DOI, or OpenAlex Work
   identifier;
2. the server classifies and normalizes the query without letting user input
   choose an arbitrary upstream URL;
3. one application-scoped async HTTP client uses explicit connection limits,
   connect/read/write/pool timeouts, and a bounded retry budget;
4. OpenAlex responses are validated through provider-specific Pydantic models
   before entering product logic;
5. abstracts are reconstructed deterministically from the provider's inverted
   index and are never summarized or expanded by an LLM;
6. papers, authors, institutions, topics, paper-specific affiliations, and
   provenance are normalized, deduplicated, and idempotently persisted;
7. malformed individual records produce a reviewable partial result when valid
   records remain, while total provider failures use safe structured errors;
8. an application-owned cache interface and bounded process-local TTL cache
   reduce repeated upstream searches without introducing Redis;
9. the frontend has an accessible, responsive live-paper workspace with
   loading, empty, partial, error, and complete states;
10. provider order is labelled as provider order, not a Research Bridge ranking;
11. the deterministic recruiter demo remains available and unchanged for the
    end-to-end mentor, draft, opportunity, and tracker journey; and
12. representative OpenAlex fixtures and an isolated local provider stub keep
    automated tests deterministic and free of external API cost.

## 2. Starting state and preservation

- Phase 5 is committed as `72d63a6`; the working tree was clean when this plan
  began.
- The existing `/api/v1/demo/*` routes intentionally use fictional fixtures and
  must remain deterministic.
- The discovery UI currently assumes a mock result made of mentor IDs. A real
  Phase 6 search cannot reuse that response shape because mentor derivation is a
  Phase 7 responsibility.
- SQLAlchemy already models papers, authors, institutions, paper-author links,
  topics, and generic provenance, but the model lacks an OpenAlex institution
  ID and paper-specific many-to-many affiliations.
- `Author.institution_id` cannot truthfully represent every institution listed
  on a historical paper. It remains nullable and is not populated from one
  arbitrary authorship affiliation.
- `httpx2` is currently a development dependency because Starlette's test
  client uses it. Phase 6 promotes the same maintained package to a runtime
  dependency for outbound asynchronous requests; no second HTTP library is
  added.
- The owner's earlier commits remain untouched and no secret, API key, private
  profile, or generated personal data may enter Git.

## 3. Current external constraints

The implementation follows current official provider behavior rather than old
OpenAlex tutorials:

- the base API is `https://api.openalex.org`;
- text search uses the Works collection `search` parameter;
- DOI and OpenAlex ID lookups use the singleton Work endpoint;
- list requests are bounded to at most 25 works in this product phase, even
  though OpenAlex permits larger pages;
- `select` limits the response to fields Research Bridge actually validates;
- API keys are optional for a small anonymous daily allowance but recommended
  for a larger free allowance;
- the key is supplied only from a server environment variable and is never
  returned, logged, embedded in error details, or exposed through
  `NEXT_PUBLIC_*`;
- response rate-limit headers are parsed for safe operational metadata;
- `403`, `429`, transport failures, and `5xx` responses remain distinguishable;
- retries use capped exponential backoff and apply only to idempotent GETs and
  transient failures.

References:

- [OpenAlex API overview](https://developers.openalex.org/api-reference/introduction)
- [OpenAlex authentication and pricing](https://developers.openalex.org/guides/authentication)
- [OpenAlex error handling](https://developers.openalex.org/api-reference/errors)
- [OpenAlex Work contract](https://developers.openalex.org/api-reference/works/get-a-single-work)
- [HTTPX2 async support](https://httpx2.pydantic.dev/async/)
- [HTTPX2 transports](https://httpx2.pydantic.dev/advanced/transports/)

## 4. Scope boundary

### 4.1 Implemented in Phase 6

- server-only OpenAlex configuration using `SecretStr` for the optional key;
- application-scoped `httpx2.AsyncClient` lifecycle;
- typed OpenAlex client and provider protocol;
- text, DOI, and OpenAlex Work ID query classification;
- bounded retry/backoff and rate-limit interpretation;
- raw response validation and deterministic normalization;
- Unicode-safe names/titles and canonical external identifiers;
- abstract inverted-index reconstruction;
- response-level and persistence-level deduplication;
- one additive Alembic migration for missing academic-catalog fields;
- idempotent academic repository upserts and provenance writes;
- bounded in-memory TTL cache behind a protocol;
- `POST /api/v1/discovery/papers`;
- live paper search UI beside the existing deterministic demo mode;
- deterministic backend, frontend, migration, and Playwright coverage;
- one optional manual live smoke request that never runs in normal tests. This
  was intentionally not run during completion because no personal developer
  key was configured; deterministic tests and manual QA used the owned loopback
  provider fixture.

### 4.2 Explicitly deferred

- professor or mentor candidate derivation;
- any Research Bridge ordering, numeric score, relevance band, or ranking claim;
- citation-based prestige signals;
- Semantic Scholar, Crossref, ORCID, arXiv, or controlled website extraction;
- LLM query expansion, explanation, summarization, or drafting;
- vector search, PostgreSQL full-text search, pgvector, OpenSearch, or Redis;
- background refresh jobs, Celery, or distributed cache invalidation;
- user authentication and per-user search history;
- opportunity ingestion, email discovery, or email sending.

Other academic providers may appear only as typed protocol names or future
adapters. They must not appear as successful live sources.

## 5. Public API contract

### `POST /api/v1/discovery/papers`

Request:

```json
{
  "query": "interpretable machine learning for clinical decision support",
  "limit": 12
}
```

The query accepts:

- focused topic, method, or keyword text;
- a canonical DOI, `doi:` identifier, or `https://doi.org/...` URL; or
- an OpenAlex Work ID such as `W2741809807` or its canonical URL.

The response contains:

- `status`: `complete`, `partial`, or `empty`;
- normalized query and `queryKind`: `text`, `doi`, or `openalex-id`;
- provider metadata with source name, official source URL, retrieval time,
  access mode, and cache hit/miss;
- total provider matches when the provider supplies the count;
- returned and skipped record counts;
- normalized papers in provider order;
- structured, non-secret warnings for skipped records or degraded source state.

Each paper contains:

- internal UUID plus canonical OpenAlex ID and optional DOI;
- verified title, publication year/date, type, language, and venue when present;
- a bounded abstract excerpt or `null`;
- `full-abstract` or `title-only` evidence strength;
- explicit source URL and last-verified timestamp;
- OpenAlex topics and provider topic scores, which are evidence metadata rather
  than Research Bridge ranking scores;
- ordered authors with OpenAlex ID, optional ORCID, and the institutions listed
  for that authorship;
- unknown values as `null`, empty arrays, or an explicit UI label—not guesses.

Provider failures use the existing error envelope and request ID. Safe error
codes distinguish configuration, invalid provider response, timeout/network,
rate limit, rejected provider request, and temporary provider failure.

## 6. Query classification and request safety

The service normalizes NFKC Unicode and whitespace before classification.

Classification order:

1. canonical OpenAlex Work URL or `W` identifier;
2. DOI URL, `doi:` value, or raw `10.<registrant>/<suffix>` value;
3. ordinary text search.

Malformed values that clearly claim to be an OpenAlex ID or DOI receive a 422
field error instead of silently becoming a text search. Text remains bounded in
length and must contain meaningful non-whitespace content.

The client builds all requests from a configured, validated provider base URL
and encoded parameters. User input never becomes a scheme, host, port, or raw
request URL. Production accepts only the official HTTPS OpenAlex host; loopback
HTTP is allowed only in `test` or `e2e` environments for deterministic stubs.

## 7. Provider client and lifecycle

```text
FastAPI lifespan
  -> one bounded AsyncClient connection pool
  -> OpenAlexClient
  -> PaperDiscoveryService
  -> close client on shutdown
```

The client has:

- explicit connect, read, write, and pool timeout settings;
- explicit maximum and keep-alive connection counts;
- redirects enabled because OpenAlex can redirect merged entities;
- a stable product user agent;
- at most three total attempts;
- injected async sleep and clock functions for deterministic retry tests;
- capped exponential delays with optional bounded `Retry-After` support;
- no request URL logging because the query string can contain the API key;
- typed provider exceptions that never expose secret-bearing URLs.

Retry behavior:

| Failure | Behavior |
| --- | --- |
| connect/read timeout or transient network error | Retry within the attempt budget. |
| `500`, `502`, `503`, `504` | Retry with capped backoff. |
| `403` provider throttling | Do not loop aggressively; surface a safe rate-limit failure, using reset metadata when available. |
| `429` exhausted daily credit | Surface a safe rate-limit failure; an immediate retry cannot restore daily credit. |
| `400` invalid provider request | No retry; treat as an adapter defect or rejected query. |
| `404` exact identifier | Return an honest empty result. |
| invalid JSON or invalid envelope | No retry after a successful HTTP response; surface an invalid-source-response error. |

## 8. Provider models and normalization

Provider DTOs live outside public API schemas. They tolerate unknown additional
provider fields but strictly validate every field Research Bridge consumes.
Optional provider metadata remains optional.

Normalization rules include:

- strip the canonical OpenAlex URL prefix from entity IDs for storage;
- lowercase DOI values and remove `doi:`/resolver prefixes;
- preserve user-facing international characters while deriving NFKC,
  case-folded matching keys;
- collapse title/name/topic whitespace without changing display spelling;
- reconstruct an abstract by placing each token at its declared positions;
- reject negative, non-integer, duplicated-conflicting, or unreasonably large
  abstract positions at the record boundary;
- cap stored abstract length and API excerpt length defensively;
- use `full-abstract` only when a validated reconstructed abstract exists;
- use `title-only` when no validated abstract exists;
- reject works without a usable ID, title, or publication year;
- retain retraction status and exclude retracted works from normal discovery
  results with an explicit skipped-record warning;
- preserve author order and corresponding-author state;
- retain every valid authorship institution instead of selecting one arbitrary
  affiliation;
- normalize ROR and ORCID identifiers without inventing missing identifiers;
- deduplicate topics by OpenAlex topic ID first, then normalized display name;
- calculate a stable SHA-256 hash over the normalized provider-owned fields for
  provenance change detection.

## 9. Database migration

An additive Phase 6 Alembic migration updates the academic catalog:

- `institutions.openalex_id`: nullable, indexed, unique;
- `papers.work_type`: nullable provider classification;
- `papers.language`: nullable ISO language code;
- `papers.is_retracted`: non-null boolean with a safe default;
- `paper_topics.openalex_topic_id`: nullable provider identifier;
- `paper_topics.score`: nullable provider topic score constrained to `[0, 1]`;
- `paper_author_institutions`: paper-specific ordered many-to-many affiliation
  table referencing the paper-author pair and normalized institution.

`Author.institution_id` remains for a future explicitly verified current or
last-known affiliation. Phase 6 does not misuse a historical paper affiliation
as a current professor fact.

The migration is upgradeable from Phase 5, reversible to the Phase 5 schema,
renders valid PostgreSQL DDL, and has zero ORM/migration drift.

## 10. Deduplication and persistence

The deterministic identity order is:

### Papers

1. canonical OpenAlex Work ID;
2. canonical DOI;
3. exact normalized title and publication year only as a conservative lookup
   candidate, never as an unconditional uniqueness claim.

### Authors

1. canonical OpenAlex Author ID;
2. canonical ORCID;
3. exact normalized name only when no external identifier exists, with no claim
   that similarly named people are the same person.

### Institutions

1. canonical OpenAlex Institution ID;
2. canonical ROR;
3. normalized name plus known country code.

The academic repository:

- eagerly loads the aggregate needed for replacement;
- upserts public entities without overwriting verified values with nulls;
- replaces provider-owned authorship/topic child rows in one transaction;
- writes one provenance record per changed paper, author, and institution;
- updates `last_verified_at` even when content is unchanged;
- flushes but does not commit;
- relies on the request transaction dependency to commit or roll back all
  normalized records atomically;
- returns stored internal IDs for the public response.

## 11. Cache boundary

```python
class PaperSearchCache(Protocol):
    async def get(self, key: SearchCacheKey) -> CachedProviderResult | None: ...
    async def set(self, key: SearchCacheKey, value: CachedProviderResult) -> None: ...
```

The first implementation is a bounded, concurrency-safe, application-scoped
TTL memory cache:

- maximum entry count and TTL are settings with conservative bounds;
- keys contain normalized query kind/value, limit, provider, and normalizer
  version;
- values contain validated normalized provider DTOs, not database sessions or
  ORM instances;
- complete and empty results may be cached; partial/error results are not;
- a cache hit still runs idempotent persistence so a prior transaction failure
  cannot create an unpersisted response;
- entries expire lazily and least-recently-used entries are evicted at capacity;
- the response states whether the provider result came from cache;
- Redis is deferred until measured multi-process load justifies it.

## 12. Backend architecture

```text
POST /api/v1/discovery/papers
  -> request validation and request ID
  -> PaperDiscoveryService
     -> QueryClassifier
     -> PaperSearchCache
     -> AcademicProvider protocol
        -> OpenAlexClient / HTTPX2
        -> raw OpenAlex Pydantic models
     -> OpenAlexNormalizer
     -> deterministic deduplicator
     -> AcademicRepository
        -> SQLAlchemy session
        -> papers/authors/institutions/topics/affiliations/provenance
  -> typed public response
  -> request transaction commit
```

Planned modules:

```text
app/
  api/v1/routes/discovery.py
  clients/openalex.py
  dependencies/discovery.py
  providers/base.py
  providers/openalex/models.py
  providers/openalex/normalizer.py
  repositories/academic.py
  schemas/discovery.py
  services/discovery.py
  services/search_cache.py
```

Names may be adjusted if the implementation shows a simpler boundary, but the
direction `route -> service -> provider/repository -> API/database` remains
fixed.

## 13. Frontend experience

The discovery page gains an explicit mode switch:

1. **Live OpenAlex papers** — real provider search and paper evidence;
2. **Recruiter demo** — the existing deterministic mentor journey and visible
   complete/partial/empty/error scenario selector.

The live mode is a separate typed state boundary, not merged into the demo
reducer. It uses React Hook Form + Zod for query/limit validation and TanStack
Query mutation state for the server request.

Live result presentation:

- “OpenAlex provider order · not Research Bridge ranked” label;
- flat editorial list with restrained teal/indigo accents;
- paper title, year, venue or `Unknown`, type/language when known;
- abstract excerpt or cautious title-only message;
- topic chips labelled as OpenAlex topic metadata;
- ordered authors and paper-specific affiliations;
- DOI and OpenAlex source links with accessible names;
- retrieved time, cache indicator, and skipped-record counts;
- a Phase 7 notice explaining that professor candidates are not derived yet.

State behavior:

- loading uses honest text and skeletons, not fake percentages;
- empty suggests a broader text query or checking an identifier;
- partial preserves valid papers and shows exactly what was skipped;
- structured errors show a retry action and request reference;
- abort signals cancel obsolete browser requests;
- result links open safely with `noopener noreferrer`;
- the layout remains usable at 390px, keyboard-only navigation, 200% zoom, and
  reduced motion.

## 14. Representative fixtures and test strategy

Fixtures cover:

- Unicode title, author, and institution names;
- DOI and OpenAlex identifiers in canonical URL form;
- a reconstructed abstract inverted index;
- title-only evidence;
- multiple authors and multiple affiliations for one authorship;
- missing venue, date, ORCID, ROR, language, and topic fields;
- duplicate work records;
- a retracted work;
- one malformed record inside an otherwise valid response;
- empty results and provider error envelopes.

### Unit tests

- query classification and malformed identifier rejection;
- ID, DOI, ORCID, ROR, Unicode, title, and topic normalization;
- abstract reconstruction, bounds, and evidence-strength selection;
- deterministic deduplication and stable content hashes;
- TTL expiry, LRU eviction, cache-key versioning, and concurrency safety;
- retry attempt counts, backoff, timeout, rate-limit, `404`, `4xx`, and `5xx`;
- API keys never appear in exceptions, logs, or public responses.

### Repository and migration tests

- Phase 5 -> Phase 6 upgrade, head check, drift check, and downgrade;
- new indexes, constraints, composite foreign keys, and affiliation ordering;
- first ingestion creates the complete aggregate and provenance;
- repeat ingestion is idempotent;
- changed provider fields update values and provenance hash;
- null provider fields do not erase previously verified identifiers;
- one failed child write rolls back the full search persistence transaction;
- SQLite remains the fast fixture database and PostgreSQL receives a live smoke
  gate before the phase is marked complete.

### Client, service, API, and contract tests

- text search, DOI lookup, and OpenAlex ID lookup build encoded requests;
- complete, empty, partial, timeout, invalid-response, rate-limit, and
  configuration outcomes use stable contracts;
- valid results remain visible when another provider record is malformed;
- OpenAPI export and generated TypeScript client remain in sync;
- frontend runtime Zod parsing rejects contract drift.

### E2E

The existing E2E runner starts an in-process loopback OpenAlex stub and points
the test-only API configuration at it. The stub verifies the API key remains a
server concern and returns representative provider JSON. Playwright verifies:

- live search loading -> complete results;
- source/DOI evidence links and provider-order label;
- title-only and unknown metadata rendering;
- repeated search cache behavior;
- deterministic demo mode still completes its existing critical journey;
- no request reaches the real OpenAlex service during automated tests.

## 15. Dependency decisions

| Dependency | Change | Reason |
| --- | --- | --- |
| `httpx2` | Move from development-only to backend runtime | Maintained async HTTP client already present through the FastAPI test stack; supplies typed async clients, connection pooling, explicit timeouts, and mock transports. |

No retry package is added. The narrow, idempotent retry policy is small enough
to implement explicitly and test completely. No Redis, task queue, vector
database, scraping library, or LLM SDK is introduced.

## 16. Quality gates

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run alembic upgrade head --sql
uv run python -m scripts.export_openapi --check

Set-Location ../web
npm.cmd run api:check
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd audit --omit=dev --audit-level=high

Set-Location ../..
docker compose --env-file .env.example config --quiet
git diff --check
```

Additional gates:

- disposable PostgreSQL 17 migration and ingestion smoke test;
- optional one-query no-key or developer-key OpenAlex smoke test, clearly
  reported and never required by deterministic CI;
- manual desktop and 390px browser QA for live complete results, cache, links,
  mode switching, responsive overflow, and console health; deterministic API,
  UI, and E2E tests cover empty, partial, and error contracts;
- secret scan confirming no API key or private profile content is tracked.

## 17. Milestones

### A. External boundary

- [x] Add and validate server-only OpenAlex settings.
- [x] Add application-scoped async HTTP lifecycle.
- [x] Add provider protocol, raw models, client, and retry policy.
- [x] Add query classification and normalization.

### B. Durable normalized catalog

- [x] Add the Phase 6 migration and ORM fields/affiliation model.
- [x] Add academic repository protocol and SQL implementation.
- [x] Add deterministic deduplication and provenance hashes.
- [x] Verify idempotent ingestion and rollback.

### C. Search service and API

- [x] Add bounded cache protocol and memory implementation.
- [x] Add the paper discovery service and structured provider errors.
- [x] Add the live discovery route and OpenAPI contract.
- [x] Regenerate and runtime-check the TypeScript client.

### D. Frontend

- [x] Add the live/demo discovery mode switch.
- [x] Add the accessible live search form and server state.
- [x] Add complete, empty, partial, error, and loading states.
- [x] Add responsive evidence-first paper results.

### E. Verification and teaching

- [x] Add provider, normalization, cache, repository, migration, API, UI, and
      E2E tests.
- [x] Pass SQLite, PostgreSQL, backend, frontend, contract, and browser gates.
- [x] Update README, API README, ROADMAP, and learning log.
- [x] Review the full diff and scan for secrets/private data.
- [x] Commit Phase 6 as one reviewable unit.

## 17.1 Completion evidence

- Backend: Ruff lint and format checks passed, mypy passed for 59 source files,
  all 48 pytest tests passed, and the checked-in OpenAPI document matched the
  application.
- Frontend: ESLint and strict TypeScript passed, all 22 Vitest tests passed,
  the generated TypeScript client matched OpenAPI, and the optimized Next.js
  production build completed.
- Full stack: seven isolated Playwright journeys passed against a migrated
  temporary SQLite database and an owned loopback OpenAlex provider. Coverage
  includes live evidence, cache visibility, keyboard tabs, the recruiter
  journey, explicit failures, mobile flow, reduced motion, and horizontal
  overflow across 360, 390, 768, and 1280px.
- PostgreSQL: a disposable PostgreSQL 17 database reached migration head with
  zero drift; ingestion produced 2 papers, 3 authors, 2 institutions, 3
  paper-author rows, 3 paper-specific affiliation links, 2 topics, and 7
  provenance records. A fresh-process replay kept those counts stable, and
  downgrade then re-upgrade succeeded.
- Manual browser QA: desktop and 390px live search, Unicode metadata,
  title-only uncertainty, DOI/OpenAlex links, cache hits, data-mode switching,
  document width, and console health passed. No warning or error was captured.
- Supply chain and hygiene: the production npm graph reported zero known
  vulnerabilities; Compose configuration and `git diff --check` passed; scans
  found no secret, private key, private profile, or real API credential.
- Optional external smoke: not run because no personal OpenAlex key was
  configured. No test contacted the real provider or consumed external
  allowance.

## 18. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| OpenAlex schema evolves | Separate provider DTOs from public schemas, ignore unknown provider fields, and validate every consumed field. |
| API key leaks through URLs or errors | Use `SecretStr`, never log upstream URLs/query parameters, catch transport errors, and add leak tests. |
| API limits make the demo unreliable | Keep deterministic demo mode, use bounded caching, expose access mode, and run automated tests only against fixtures/stubs. |
| Retries amplify outages or consume credits | Retry only transient idempotent failures with three total attempts and capped backoff; do not aggressively retry daily-credit exhaustion. |
| Bad record hides good records | Validate per record, retain valid records, and return `partial` with skipped counts/warnings. |
| Historical affiliation is shown as current | Store affiliations on the paper-author relationship and leave current academic role/institution unknown. |
| Duplicate provider data creates duplicate rows | Canonical external IDs, deterministic fallback matching, unique constraints, and idempotency tests. |
| Cache serves uncommitted ORM state | Cache provider DTOs only and repeat persistence on cache hits. |
| In-memory cache is mistaken for distributed infrastructure | Document process-local behavior and defer Redis until measured load requires it. |
| Provider order is mistaken for ranking | Label it visibly and omit Research Bridge scores, bands, and fit explanations until Phase 7. |
| Live mode breaks recruiter reliability | Preserve the deterministic demo as a first-class adjacent mode and keep its existing E2E journey. |

## 19. Teaching targets

The Phase 6 learning-log entry must explain:

- provider DTOs versus public API schemas;
- dependency inversion through a provider protocol;
- async connection pooling and application lifespan;
- connect/read/write/pool timeouts;
- idempotency, retry budgets, backoff, and rate limits;
- query normalization and SSRF-safe request construction;
- inverted-index abstract reconstruction;
- identity normalization and conservative deduplication;
- many-to-many paper authorship affiliations;
- transactions, upserts, and provenance hashes;
- cache-aside behavior and why process-local cache is limited;
- partial success as a product contract;
- why provider ordering is not a ranking model.

## 20. Rollback

- Phase 5 remains recoverable as `72d63a6`.
- The Phase 6 migration downgrades to the Phase 5 schema without changing the
  initial migration.
- Provider tests use local fixtures and do not mutate remote systems.
- E2E uses an isolated database, owned API/web processes, and an owned loopback
  provider stub.
- No automated command targets an unknown developer database.

## 21. Completion rule

Phase 6 is complete only when real OpenAlex paper retrieval is typed, bounded,
safe, normalized, provenance-preserving, idempotently persisted, visibly honest
about partial/unknown data, fully represented in the frontend, deterministic in
automated tests, manually reviewed at desktop/mobile sizes, documented for the
owner to explain, and committed with no ranking or professor-candidate claim.

The exact next step after acceptance is **Phase 7 — Basic relevance and
evidence**: derive mentor candidates from persisted authors and supporting
papers, then add a transparent deterministic heuristic and feature
contributions without calling it a research-grade ranking model.
