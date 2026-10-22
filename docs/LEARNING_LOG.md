## Phase 10 — Authentication, Privacy, Security

### What was built
Phase 10 introduced a full authentication boundary and privacy model to Research Bridge AI. Every user's data — profile, saved items, drafts, applications — is now owned by an authenticated identity rather than an anonymous demo session.

**Backend additions:**
- **`security_headers.py`** — HTTP middleware injecting X-Content-Type-Options, X-Frame-Options: DENY, Referrer-Policy, Permissions-Policy, and CSP `frame-ancestors none`
- **`rate_limit.py`** — In-process sliding-window IP rate limiter; 30 req/60 s on the expensive discovery endpoint
- **`account_deletion.py`** — `AccountDeletionService.delete_authenticated_owner()` cascades all private rows via SQLAlchemy ORM relationships in a single transaction
- **`account.py` route** — `DELETE /api/v1/account` (204, requires JWT)

**Frontend additions:**
- `@supabase/supabase-js` browser client in `src/lib/supabase/client.ts`
- `configureApiClient()` in `src/lib/api/setup.ts` — injects `Authorization: Bearer <token>` on every API call
- `useAuth()` hook — subscribes to `onAuthStateChange`
- `<AuthGuard>` — redirects `/profile`, `/applications`, `/opportunities` to `/login` if unauthenticated
- Login/sign-up form at `/login`

### Why it exists
Without authentication, anyone could read or delete anyone else's data. Phase 10 enforces that every private read and write filters by `owner_id`. The Supabase JWT is verified RS256 using JWKS (cached 600 s).

### Concepts introduced
- **RS256 JWT verification** — asymmetric signing means the backend never needs the Supabase secret to verify tokens
- **JWKS caching** — avoids a network call per request while allowing key rotation
- **Cascade delete via ORM** — SQLAlchemy `cascade="all, delete-orphan"` lets one DELETE on the root row clean up all dependent tables
- **Sliding-window rate limit** — a `collections.deque` of timestamps, O(1) pop/append
- **Security headers** — defense-in-depth headers reduce clickjacking and MIME-sniffing risk

### Data flow
```
Browser → Supabase Auth → access_token (RS256 JWT)
→ Next.js API interceptor adds Authorization header
→ FastAPI HTTPBearer extracts token
→ SupabaseTokenVerifier verifies against cached JWKS
→ SqlAlchemyOwnerRepository.get_or_create_authenticated(subject)
→ AuthenticatedPrincipal(owner_id, subject)
→ All repos filter by owner_id
```

### Important files
| File | Purpose |
|---|---|
| `apps/api/app/core/security_headers.py` | HTTP security headers |
| `apps/api/app/core/rate_limit.py` | Sliding-window limiter |
| `apps/api/app/services/account_deletion.py` | Owner cascade |
| `apps/api/app/api/v1/routes/account.py` | DELETE /account |
| `apps/web/src/lib/supabase/client.ts` | Browser Supabase client |
| `apps/web/src/lib/api/setup.ts` | Token injection |
| `apps/web/src/features/auth/` | Login form, guard, hook |

### How to run / test
```bash
# Backend tests
cd apps/api
uv run pytest --basetemp=.test-tmp-phase10 -p no:cacheprovider

# Frontend typecheck
cd apps/web
npm.cmd run typecheck
```

### Common errors
- **401 on every request**: check that `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `apps/web/.env.local` match your Supabase project
- **uvicorn SUPABASE_URL validation error**: `SUPABASE_URL` in `apps/api/.env` must end with `.supabase.co`

### Limitations
- Rate limiter is in-process (not shared across workers/pods); Redis will replace it in Phase 12
- No email MFA; Supabase OTP is not enabled yet

### Next step
Phase 11 — LangGraph workflow orchestration

---

## Phase 11 — LangGraph Workflow Orchestration

### What was built
Phase 11 introduces a durable, checkpointed, two-phase workflow using LangGraph — the selected orchestrator for Research Bridge AI. The workflow persists its state in PostgreSQL between the two human decision points:

1. **Mentor discovery** — deterministic paper retrieval and ranking (no LLM)
2. **Human checkpoint** — user selects mentor + 1-2 supporting papers
3. **Draft generation** — evidence-grounded outreach email (LLM optional; deterministic fallback)

**Backend additions:**
- `apps/api/app/workflow/state.py` — `PlacementWorkflowState` TypedDict: typed fields for query, owner, discovery result, selection, draft result
- `apps/api/app/workflow/graph.py` — two async nodes (`discover_mentors`, `generate_draft`) + `build_placement_graph()` with conditional routing
- `apps/api/app/api/v1/routes/workflow.py` — three endpoints:
  - `POST /api/v1/workflow/start` → creates thread, stores initial state
  - `POST /api/v1/workflow/{id}/resume` → injects selection, re-connects graph
  - `GET /api/v1/workflow/{id}/stream` → SSE stream of `updates` events
- `apps/api/app/main.py` — lifespan now opens a `psycopg3 AsyncConnectionPool` with `dict_row` factory, creates `AsyncPostgresSaver`, calls `checkpointer.setup()` on startup
- Packages added: `langgraph`, `langgraph-checkpoint-postgres`, `psycopg`, `psycopg-pool`

**Frontend additions:**
- `apps/web/src/features/workflow/use-workflow.ts` — `useWorkflow()` hook with typed state machine (idle → discovering → awaiting_selection → generating → done | error). Uses `fetch + ReadableStream` instead of EventSource to support the `Authorization` header.
- `apps/web/src/features/workflow/workflow-panel.tsx` — Full two-phase UI: search bar → candidate list → paper checkboxes → "Generate Draft" → draft review. No auto-send.
- `apps/web/src/app/discover/page.tsx` — Added the `<WorkflowPanel>` in a side-by-side layout next to DiscoveryExperience

### Why it exists
LangGraph gives us:
- **Durable state** — a workflow can be paused between Phase 1 and Phase 2 across requests, across restarts; state is checkpointed in Postgres
- **Typed transitions** — the `PlacementWorkflowState` TypedDict makes node inputs/outputs explicit and testable
- **Honest progress** — SSE events are emitted per node completion, not per LLM token, so the UI shows real milestones
- **Human-in-the-loop** — the graph naturally pauses at `END` after discovery; the human is required to supply selection before the graph continues

### Concepts introduced
- **LangGraph `StateGraph`** — nodes are pure async functions `(state, config) -> state_patch`; edges route between them
- **LangGraph `AsyncPostgresSaver`** — stores checkpoint snapshots in `langgraph_checkpoints` table (auto-created by `checkpointer.setup()`)
- **`configurable` dict** — LangGraph's mechanism to pass request-scoped objects (like `mentor_service`, `outreach_service`) into nodes without making them part of serialized state
- **Server-Sent Events (SSE)** — lightweight unidirectional streaming; browser reads `text/event-stream` line by line; double-newline terminates a message
- **`stream_mode="updates"`** — LangGraph emits a dict `{ node_name: state_patch }` per node, so we know exactly which node produced which output

### Data flow
```
Browser
  → POST /workflow/start → thread_id
  → GET  /workflow/{id}/stream (SSE)
      ↳ discover_mentors node:
          PaperDiscoveryService.search() → OpenAlex API
          MentorDiscoveryService.search() → deterministic scoring
          → { discovery_response: {...} }
      ↳ graph hits END (no selection yet)
      ↳ SSE closes
  → User selects mentor + papers in WorkflowPanel
  → POST /workflow/{id}/resume → state patched
  → GET  /workflow/{id}/stream (SSE again from new state)
      ↳ generate_draft node:
          OutreachService.create() → evidence-grounded draft
          → { draft_response: {...} }
      ↳ graph hits END
      ↳ "event: complete" SSE sent
  → Draft rendered for review
```

### Important files
| File | Purpose |
|---|---|
| `apps/api/app/workflow/state.py` | Typed graph state |
| `apps/api/app/workflow/graph.py` | Node functions + graph builder |
| `apps/api/app/api/v1/routes/workflow.py` | 3 HTTP endpoints |
| `apps/api/app/main.py` | Psycopg pool + checkpointer lifespan |
| `apps/web/src/features/workflow/use-workflow.ts` | SSE consumer + state machine |
| `apps/web/src/features/workflow/workflow-panel.tsx` | Two-phase UI |

### How to run / test
```bash
# Backend quality gates
cd apps/api
uv run ruff check .
uv run mypy app
uv run pytest --basetemp=.test-tmp-phase11 -p no:cacheprovider

# Frontend
cd apps/web
npm.cmd run typecheck
npm.cmd run lint
```

To exercise the workflow manually:
1. Start backend: `cd apps/api && uv run uvicorn app.main:app --reload`
2. Start frontend: `cd apps/web && npm.cmd run dev`
3. Sign in at `/login`, navigate to `/discover`
4. Type a query in "Guided placement journey" and click "Find Mentors"
5. Select a mentor, pick 1-2 papers, click "Generate Outreach Draft"
6. Review the draft — it will never be sent automatically

### Common errors
- **`SUPABASE_URL` validation error on lifespan**: the psycopg URL is built by replacing `postgresql+asyncpg` with `postgresql`; ensure `DATABASE_URL` in `.env` uses the asyncpg prefix
- **`langgraph_checkpoints` table missing**: `checkpointer.setup()` creates it; if you see this error, the startup pool failed — check DB connectivity
- **SSE stream closes immediately**: check that the thread ID was created before streaming (call `/start` first)

### Limitations
- The psycopg pool shares the app lifespan but is separate from the SQLAlchemy pool — in production these should use the same connection limits
- Workflow state is not scoped by `owner_id` at the LangGraph level (thread IDs are UUIDs so practically unguessable, but there is no access check on the stream endpoint beyond JWT auth) — Phase 12 should add owner→thread mapping
- No frontend loading skeletons yet on the candidate list

### Next step
Phase 13 — Production hardening (Redis caching, rate limiting, deployment config)

---

## Phase 12 — Quality & Observability

### What was built
Three pillars of quality infrastructure that close the loop between "it works" and "we can measure how well it works":

1. **Structured observability** — `JsonFormatter` now auto-injects the per-request `request_id` from a `ContextVar` into every structured log line, so any log entry can be correlated to a specific API request.
2. **Retrieval quality evaluation script** — `evaluate_retrieval.py` runs benchmark queries against the live OpenAlex pipeline (via `httpx.ASGITransport`) and reports Recall@5, Recall@10, MRR, duplicate rate, and evidence coverage.
3. **End-to-end accessibility audits** — `@axe-core/playwright` is integrated into the Playwright E2E suite to catch WCAG violations automatically on every test run.

### Why it exists
The roadmap requires measured retrieval quality (not just "it returns results"). The AGENTS.md rules mandate Recall@5, Recall@10, MRR, nDCG@10, duplicate rate, evidence coverage, unsupported-claim rate, and latency percentiles. This phase builds the measurement infrastructure so those metrics can be tracked over time.

Accessibility audits exist because the project targets an academic audience that includes screen reader users, keyboard-only navigators, and users with reduced motion preferences.

### Concepts introduced
- **ContextVar-based request correlation** — Python's `contextvars.ContextVar` propagates a UUID across all log calls within a single async request without thread-local hacks.
- **ASGI transport testing** — `httpx.ASGITransport` lets you run HTTP requests against a FastAPI app in-process without starting a server, enabling fast integration-level evaluation scripts.
- **axe-core accessibility auditing** — `@axe-core/playwright` runs the Deque axe engine inside Playwright's browser, returning structured violation reports that can be asserted in tests.
- **E2E auth bypass pattern** — A `NEXT_PUBLIC_E2E_TEST` environment variable short-circuits Supabase session checks in both the React `useAuth` hook and the API client interceptor, while the backend uses `SUPABASE_TEST_BEARER_TOKEN` for a fixed token verifier.

### Data flow
```
evaluate_retrieval.py
  → sets DATABASE_URL to sqlite+aiosqlite:///:memory:
  → calls create_app() to build a real FastAPI app
  → creates tables via Base.metadata.create_all()
  → sends POST /api/v1/discovery/mentors via httpx ASGITransport
  → collects candidates, computes Recall@K, MRR, duplicate rate
  → prints summary report

E2E accessibility flow:
  Playwright test
  → navigates to a page
  → AxeBuilder({ page }).analyze()
  → asserts violations.length === 0
```

### Important files
| File | Purpose |
|------|---------|
| `apps/api/app/core/logging.py` | `JsonFormatter` with `request_id` injection |
| `apps/api/scripts/evaluate_retrieval.py` | Retrieval quality evaluation script |
| `apps/web/e2e/demo-journey.spec.ts` | E2E tests with axe-core accessibility checks |
| `apps/web/src/features/auth/use-auth.ts` | Auth hook with E2E bypass via initial state |
| `apps/web/src/lib/api/setup.ts` | API interceptor with E2E token injection |
| `apps/web/src/features/demo/components/demo-notice.tsx` | Added `aria-label` to aside |
| `apps/web/src/features/discovery/discovery-experience.tsx` | Added `aria-label` to aside |

### How to run / test
```bash
# Backend quality gates
cd apps/api
uv run ruff check .
uv run pytest --basetemp=.test-tmp -p no:cacheprovider

# Retrieval evaluation (requires network for OpenAlex)
cd apps/api
$env:PYTHONPATH="."
uv run python scripts/evaluate_retrieval.py

# Frontend quality gates
cd apps/web
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test:e2e   # runs 9 E2E tests including axe-core
```

### Common errors
- **`PermissionError` on pytest temp dir** — on Windows, use `--basetemp=.test-tmp` to avoid the locked system temp directory
- **409 "profile_required" on outreach draft** — the live `/api/v1/outreach/drafts` endpoint requires a saved profile for the authenticated user; E2E tests seed one via `PUT /api/v1/profile` before creating drafts
- **axe-core violation on `<aside>`** — every `<aside>` element needs a unique `aria-label` or `aria-labelledby` attribute; without it, screen readers cannot distinguish between multiple complementary landmarks

### Limitations
- The evaluation script uses in-memory SQLite so it cannot test the authenticated outreach draft endpoint (which needs a profile + owner record); it measures retrieval quality only
- nDCG@10 is not yet computed (requires graded relevance judgments, not just binary hit/miss)
- Latency percentiles (p50, p95, p99) are not yet tracked — the script reports only average latency
- axe-core checks run only on `/profile` and `/discover` pages; other routes should be added incrementally

### Next step
Phase 14 — Post-placement ranking and enrichment research

---

## Phase 13 — Deployment and Portfolio Release

### What was built
The final pre-release hardening and deployment configuration, preparing the project for a portfolio showcase:
1. **Dockerization** — Multi-stage `Dockerfile`s for Next.js (standalone) and FastAPI (using `uv`).
2. **Orchestration** — A complete `docker-compose.yml` that brings up PostgreSQL (pgvector), Redis, the API, and the Web frontend.
3. **CI/CD Pipeline** — GitHub Actions (`.github/workflows/main.yml`) for automated linting, type checking, and testing (including Playwright E2E with browser provisioning).
4. **Production Hardening** — Integrated Redis and `fastapi-limiter` for rate limiting API routes. Created a graceful failure mechanism so local development works without Redis.
5. **Documentation** — A completely rewritten `README.md` with Mermaid architecture diagrams, a deployment runbook (`docs/deployment.md`), and a `docs/recruiter-interview-script.md`.

### Why it exists
The placement release gate in `ROADMAP.md` dictates that the project must be fully deployable with rollback and incident runbooks. A portfolio project isn't just about the code; it's about how the code is presented, maintained, and operated in a production-like environment. 

### Concepts introduced
- **Next.js Standalone Output** — Trims the Next.js production build to only include the `node_modules` strictly necessary for the application, drastically reducing the Docker image size.
- **FastAPI Graceful Degradation** — The application attempts to initialize Redis on startup, but safely catches connection errors and disables rate-limiting rather than crashing the API.
- **`fastapi-limiter` Dependency** — A simple library to wrap FastAPI routes with Redis-backed token buckets.
- **Multi-stage `uv` Docker Builds** — Using Astral's `ghcr.io/astral-sh/uv` as a builder image to quickly synchronize dependencies before copying in the application source.

### Data flow
```
User Request
  → Next.js (port 3000)
    → Next.js rewrite /backend/*
      → FastAPI (port 8000)
        → Custom RateLimiter Dependency
          → Check Redis (port 6379) for token bucket limit
        → Route execution
```

### Important files
| File | Purpose |
|------|---------|
| `.github/workflows/main.yml` | CI/CD pipeline |
| `apps/web/Dockerfile` | Next.js production multi-stage build |
| `apps/api/Dockerfile` | FastAPI production multi-stage build |
| `docker-compose.yml` | Local orchestration |
| `apps/api/app/dependencies/rate_limiting.py` | Graceful rate limiter dependency |
| `README.md` | Polish and architecture diagrams |

### How to run / test
```bash
# Run the entire stack locally
docker compose up --build -d

# Verify API health
curl http://localhost:8000/api/v1/health

# Run CI locally (simulate GitHub Actions)
cd apps/api && uv run ruff check . && uv run mypy app && uv run pytest
cd apps/web && npm run lint && npm run typecheck && npm run test:e2e
```

### Common errors
- **`FastAPILimiter` raises HTTPException (429)** — If you trigger too many outreach drafts, the limiter correctly kicks in. Wait the specified seconds.
- **Docker Compose port conflicts** — If 5432 or 8000 are in use locally, edit the `docker-compose.yml` exposed ports (e.g., `55432:5432`).

### Limitations
- The CI pipeline does not currently deploy to a cloud provider automatically (e.g., Vercel, Render) because specific hosting targets haven't been selected.
- Redis caching is only used for rate limiting so far, not for the Discovery cache (which still uses `cachetools` in memory).

### Next step
This concludes the active roadmap! 🎉

---

## Phase 14 — Post-placement Ranking and Enrichment Research

### What was built
A research spike simulating the performance of three retrieval strategies against a labeled dataset of academic queries:
1. **Current Phase 7 Heuristic** (Keyword overlap + evidence depth)
2. **PostgreSQL Full-Text Search** (`tsvector` approximation)
3. **Dense Vector Search** (`pgvector` cosine similarity)

A report (`docs/research/ranking-evaluation.md`) was written to document the methodology and the final architectural decision.

### Why it exists
The roadmap mandated that we "adopt complexity only when measurements show a benefit." Before blindly integrating massive language models to generate embeddings for millions of academic papers, we must measure whether the latency and infrastructure cost actually improve MRR and nDCG for our specific domain (structured academic metadata).

### Concepts introduced
- **Recall@K, MRR, nDCG@10** — Standard Information Retrieval metrics to evaluate the quality of a ranked list against an ideal, human-labeled relevance baseline.
- **`pgvector`** — An open-source vector similarity search extension for PostgreSQL.
- **Latency vs. Relevance Trade-off** — The recognition that an external embedding call adds 100-200ms of synchronous latency to a query, which is unacceptable if it doesn't dramatically outperform a sub-millisecond local heuristic.

### Data flow
```
evaluate_ranking_models.py
  → Load synthetic labeled relevance judgments
  → Rank using Heuristic (simulated OpenAlex behavior)
  → Rank using tsvector (simulated PostgreSQL FTS)
  → Rank using pgvector (simulated dense embedding + cosine similarity)
  → Compute metrics (Recall@5, MRR, nDCG@10)
  → Output latency and performance report
```

### Important files
| File | Purpose |
|------|---------|
| `apps/api/scripts/evaluate_ranking_models.py` | Standalone Python evaluation script |
| `docs/research/ranking-evaluation.md` | Final decision report and metric summary |

### How to run / test
```bash
cd apps/api
$env:PYTHONPATH="."
uv run python scripts/evaluate_ranking_models.py
```

### Common errors
- **nDCG calculation assumes valid `idcg`** — If there are no relevant items for a query in the test set, `idcg` could be zero. The script clamps `idcg` to a tiny positive number to avoid division by zero.

### Limitations
- The evaluation dataset is highly synthetic and small (~5 mentors, 3 queries).
- The vector search is simulated rather than calling an actual embedding API (like OpenAI `text-embedding-3-small`), meaning real-world relevance might be slightly different. However, the *latency penalty* of external API calls remains accurate.

### Next step
This historical phase summary does not establish release readiness. Phases 15
and 16 and live deployment verification remain open. Synthetic ranking experiments
do not establish real provider latency or retrieval quality.

## 2026-10-07 — Phase 15: account profiles and private guided workflows

### What was built and why

The profile editor now reads and saves the authenticated account profile, using
the same form validation as onboarding. Mentor matching and guided outreach use
those saved facts instead of the shared demo profile. Missing profiles lead to
onboarding; failed profile requests show a retry state rather than pretending
the student has no profile.

Workflow start, stream, and resume now share an application-lifetime checkpointer.
Streaming and resuming require the stored owner to match the authenticated user.
Foreign and missing workflows return the same 404. Unavailable persistent storage
returns 503 instead of silently creating an empty checkpoint store.

The existing UI direction was preserved. Labels now describe real saved data,
workflow result fields match the API, and muted text was darkened after an axe
check measured only 4.39:1 contrast on light panels. The homepage's server-rendered
card no longer attaches a browser event handler that prevented production builds.

### Concepts and data flow

- **Account-scoped caching:** identity is part of the profile query key; changing
  accounts recreates the query cache and local UI state. Updating profile facts
  resets dependent discovery/draft screens so old evidence is not reused.
- **Authentication versus authorization:** a valid token identifies the caller;
  checking the checkpoint's owner determines whether that caller may use it.
- **Runtime contracts:** Zod validates streamed responses before rendering them.
  TypeScript alone cannot guarantee that network JSON matches a declared type.
- **Workflow state:** discovery completion pauses for mentor/paper selection;
  draft completion is a separate state. Truncated streams show an error.

Flow: sign in → account profile API → owner-scoped database record → mentor
service → evidence-backed deterministic ranking → checkpointed selection →
outreach service → saved draft. The guided panel previews the draft; the mentor
workspace supports editing, versioning, review, and copying. No email is sent.

### Important files

- `apps/web/src/features/profile/use-account-profile.ts`, `profile-guard.tsx`,
  `profile-experience.tsx`, and `src/lib/api/profile.ts`: account reads, validation,
  cache updates, and editing.
- `apps/web/src/features/onboarding/onboarding-experience.tsx` and
  `src/app/app-providers.tsx`: onboarding and identity changes.
- `apps/api/app/dependencies/mentor_discovery.py`, `app/services/workflow.py`,
  `app/api/v1/routes/workflow.py`, and `app/main.py`: authenticated composition,
  ownership enforcement, and checkpoint lifetime.
- `apps/web/src/features/workflow/`: validated streaming and selection UI.
- `apps/api/tests/test_workflow_api.py`, `test_mentor_discovery.py`, frontend
  profile/workflow/provider tests, and `apps/web/e2e/account-journey.spec.ts`:
  isolation, persistence, failure, accessibility, and journey regressions.

No new application dependencies or schema migrations were needed. The lockfile
was repaired to include the already-declared Fraunces and Hanken Grotesk fonts.
The existing rate-limit dependency's return annotation was corrected for mypy.

### How to run and debug

Use Node 24, Python 3.13, `npm ci`, and `uv sync --frozen --all-groups`. From
`apps/web`, run `npm run lint`, `npm run typecheck`, `npm run test`,
`npm run api:check`, and `npm run test:e2e`. The E2E command performs a production
build and starts isolated local API, web, and provider-fixture servers. From
`apps/api`, run `uv run ruff check .`, `uv run mypy app`, and `uv run pytest`.

On this Windows host, the sandbox blocks some test socket operations. Run the
authorized checks outside that sandbox and give pytest a fresh workspace-local
`--basetemp=.test-tmp-<unique-run>` if the shared temporary directory fails.
The system Node 26 does not match this project's engine; select Node 24 first.
The opportunity fixture's September 2026 deadline is now past, so the tracking
test explicitly includes expired records. This preserves real expiry filtering.

### Limitations and exact next step

Verification results: frontend lint and typecheck passed; 50 tests across 19
files passed; generated API consistency passed; the production build passed.
All 9 Playwright journeys passed, including accessibility and mobile checks.
Backend Ruff passed, mypy checked 101 files without errors, and all 96 pytest
tests passed. An initial pytest attempt hit shared temporary-directory setup
errors; rerunning with a fresh workspace-local base directory passed. No live
credentials were used. `git diff --check` passed.

Automated integration checks use SQLite, in-memory workflow checkpoints, isolated
test tokens, and provider fixtures. They do not verify live Supabase login,
PostgreSQL checkpoint durability, or paid model calls. Local memory workflows do
not survive a server restart. Test-only frontend builds must not be deployed.
The broader privacy audit, homepage claims/footer review, and a simpler primary
discovery action remain open. Synthetic ranking results are not production evals.

Next: run a configured Supabase/PostgreSQL smoke test with two accounts, including
sign-in, save/reload, matching, draft review, account switching, and checkpoint
recovery after restart. Keep wider visual changes in the Phase 16 review.


## 2026-10-07 — Transfer to the main Desktop checkout

At the owner's request, transferred the reviewed Phase 15 changes to
`C:/Users/afzal/Desktop/Research-Bridge AI`. Compared each affected path with
the common Git base before copying; no conflicting edits were found. Verified
42 paths, including the already-updated lockfile and replacement of the obsolete
browser test. Affected originals and a manifest are backed up under
`C:/Users/afzal/.codex/worktrees/9e72/Research-Bridge AI/.tmp/desktop-transfer-20261007-154207`.

Concept: Git worktrees have separate working files even when they share history.
Moving a tested change between them requires checking for destination edits.
No application behavior or data flow was added in this transfer. The important
files remain the profile, workflow, API contracts, tests, and documentation listed
above. Preserved the existing Desktop `next-env.d.ts` edit and conversation history;
environment files, database data, and installed dependencies were not copied.

Desktop verification: frontend lint/typecheck, all 50 unit tests, and API contract
consistency passed. Backend Ruff, mypy (101 files), and all 9 focused mentor/workflow
tests passed. Pytest reported an unwritable optional cache warning; test results
were successful. Content comparison found only the pre-existing `next-env.d.ts`
difference among tracked files. `git diff --check` passed. The production build
and 9 browser journeys previously passed in the source worktree; they were not
repeated for this content-identical transfer. Changes remain uncommitted.

Run checks from the Desktop folder using the commands above. Next step: verify
the Docker build and Supabase environment wiring from this main checkout before
claiming that the one-command startup is ready. This transfer did not fix the
separate Windows PostgreSQL port conflict or establish live-service readiness.


## 2026-10-07 — Docker startup repair in the Desktop checkout

### What changed and why

Restored local Docker startup using the existing four-service architecture.
The frontend image now uses Node 24, the root workspace lockfile, and both root
and workspace-local npm dependencies. It runs the monorepo standalone server at
`apps/web/server.js`. The API consistently installs and runs inside `/app/.venv`
with the frozen uv lockfile. No application dependency was added.

Compose loads `apps/api/.env` at runtime and mounts `apps/web/.env.local` as a
BuildKit secret for Next's build. Public Supabase configuration is embedded into
the browser bundle. The mounted environment file is removed from Next's traced
standalone output before creating the final image. Build contexts exclude host
dependencies, credentials, private files, and caches. API and web health checks
verify readiness; all published ports bind only to localhost. PostgreSQL uses
host port 5433 to avoid the existing Windows PostgreSQL service on port 5432.

Important files: `compose.yaml`, both application `Dockerfile`s, root and API
`.dockerignore`, the three `.env.example` files, and `README.md`.

### Concepts and data flow

Docker services resolve each other by service name: browser → localhost:3000 →
Next proxy → api:8000 → postgres:5432 / redis:6379. Host port 5433 is for tools
outside Docker. Build-time public settings and runtime backend settings are
separate. A Python virtual environment's executables must be on PATH. npm
workspaces may install packages under both root and application node_modules.

### Existing database repair

Startup found an orphaned Alembic marker `20260919_1508`; no corresponding
migration exists in this checkout or its Git history. Compared the existing
schema with SQLAlchemy metadata (including types and server defaults), excluding
LangGraph's independently managed checkpoint tables: zero differences. Made a
full pg_dump custom-format backup at
`private-data/docker-startup-backup/before-revision-repair.dump` (Git-ignored).
Rechecked schema equality inside a transaction and changed only the single
revision marker to the repository head `20260801_0004`. No application records
or tables were deleted or recreated. This was a one-time local repair, not an
automatic startup workaround or a new migration. Do not blindly stamp other
unknown databases; compare their schemas and retain backups first.

### Run and validation results

From `C:/Users/afzal/Desktop/Research-Bridge AI`, run:

```powershell
docker compose up --build -d
docker compose ps
```

Open http://localhost:3000. Stop without deleting volumes using
`docker compose stop`. If public frontend settings change, run
`docker compose build --no-cache web` then `docker compose up -d`; secret contents
do not invalidate cached build layers. For a host-run API, the local DATABASE_URL
must use port 5433; existing private environment files were not edited.

Both production images built. `docker compose up -d --wait` passed with all four
services healthy. Homepage, login page, direct API health, and proxied API health
returned 200. Anonymous private-profile access returned 401. The database is at
`20260801_0004` and checkpoint migrations exist. The frontend runtime image contains
no `.env*` files. Chrome smoke checks rendered the email login form and redirected
anonymous profile navigation to login with zero browser runtime errors. The first
browser attempt used an absent bundled Chromium; the project's configured Chrome
channel passed. Compose validation and diff whitespace checks passed. The earlier
50 frontend/96 backend/9 browser suite results remain recorded above; this change
was validated with actual Docker build and startup checks.

### Remaining limitation and next step

Supabase frontend/backend origins match and the frontend JWT key role is anon,
but the configured project hostname fails DNS resolution on Windows and inside
the API container. The general supabase.com hostname resolves. Login completion
is therefore unverified and currently blocked by project reachability. The owner
needs to check the project's dashboard status and restore it or provide updated
project settings. Do not bypass authentication. After reachability is restored,
verify sign-in and the two-account profile/discovery/draft journey. OpenAlex/model
provider behavior was not tested live in this startup repair.


## 2026-10-09 — Direct university website discovery

### What was built and why

Added an explicit website-scan path on Discover for students who want evidence
from university and lab pages themselves. Choose 10/20/30 unique paper targets,
watch incremental counts, cancel without losing received results, and inspect
source links/timestamps. Internship programs have separate status, eligibility,
and work-mode evidence; unknown mode is displayed as Not specified and can be
filtered. No preference for Indian students or faculty vacancy is inferred.

### Concepts and data flow

React Hook Form + Zod validate the form; a TanStack mutation owns the request.
The browser sends an authenticated POST through the Next same-origin proxy.
FastAPI reserves a per-account scan slot, then a deterministic service traverses
reviewed university pages. Every fetch checks HTTPS/domain restrictions, DNS
public addresses, robots policy and host pacing. The actual connection is pinned
to the vetted IP while TLS verifies the original hostname. Redirects are checked
again. Server-sent events carry validated snapshots; the browser validates them
again and retains earlier evidence if the stream later fails.

Beautiful Soup is the only new direct dependency: it parses HTML without running
page scripts. Its transitive soupsieve dependency supports CSS selection. Parsing
and lexical matching happen in deterministic code, with no LLM or numeric AI
ranking score. DOI identities and arXiv version identities collapse duplicates.
A bounded priority queue favors research/publication links; relevance is based on
citation text, not the university name. Cancellation releases an ownership-token
reservation so delayed cleanup cannot remove a newer scan's reservation.

### Important files

- API: `app/clients/university.py`, `app/services/university_sources.py`,
  `university_extraction.py`, `university_scan.py`, `app/schemas/university.py`,
  `app/api/v1/routes/university.py`, router/main integration and `tests/test_university.py`.
- Web: `src/features/discovery/university-discovery.tsx`, `university-contracts.ts`,
  `src/lib/api/university.ts`, Discover page, tests and Next proxy timeout.
- Dependency lock, generated OpenAPI/client, execution plan, spec and roadmap.
  No database schema change or migration is required for request-scoped results.

### Run and test

From the Desktop project: `docker compose up --build -d`, then visit
http://localhost:3000/discover after sign-in/onboarding. Backend checks from
`apps/api`: `uv run ruff check .`, `uv run mypy app`, `uv run pytest`.
Frontend checks from `apps/web`: `npm run lint`, `npm run typecheck`,
`npm run test`, `npm run test:e2e` (includes a production build and Chrome).
Export API contracts with `uv run python -m scripts.export_openapi` in the API
folder, then `npm run api:generate` in the web folder.

### Debugging and observed results

Live tests exposed outdated directory URLs and priority-queue starvation.
Corrected the URLs and replaced lower-priority queued links when valuable
publication links arrive. A live machine-learning scan then found 20 unique
matching citations from official ISTA pages in 22 seconds. This is one smoke
query, not a retrieval benchmark or guarantee of university diversity.
IITGN returned 403 and some KAUST paths disallowed crawling. These produce source
warnings. OIST has some externally embedded publication lists, which are not
followed. Unknown work mode is not inferred from housing or campus location.
A pytest-asyncio marker initially failed because that extra plugin is not
installed; tests now use the existing AnyIO support with its asyncio backend.

### Limitations and next step

120-second/40-page/depth-3/2-MB limits and conservative HTML extraction mean
partial results are normal. Robots redirects that cannot be verified are skipped.
Source registry coverage is curated, not exhaustive; live calls change over time.
Per-process concurrency is appropriate to the current single-process deployment,
not a distributed job queue. Unsupported HTML/JS/PDF layouts, cross-identifier
preprint duplicates, professor identity linking and persistent website-result
saving remain future work. No emails are sent. Existing Supabase project
reachability still needs verification before a real-account end-to-end demo.
Next: verify Docker/browser integration, then restore the configured Supabase
project if needed and run a real student search with source evidence review.


### Final automated validation

Ruff and strict mypy passed. All 124 backend tests passed, including 28 dedicated
university tests for URL/DNS boundaries, robots denial, redirect blocking, body
limits, rate limits, extraction, deduplication, targets, stale reservation cleanup,
authentication, SSE and queue starvation. Frontend ESLint/TypeScript checks and
all 56 unit/component tests passed. Production build and all 10 Chrome browser
tests passed, including university target submission, partial-result evidence,
accessibility, and existing account/workflow flows. The university browser test
uses an explicit stream fixture; real crawling was independently smoke-tested.
Both Docker images built; OpenAPI export and generated-client checks passed.
Local diff whitespace checks passed. Supabase DNS is still unresolved, so no
real-account login success is claimed. Earlier unrelated working changes remain
present; no blanket Git commit or reset was made.


Docker startup passed with all four services healthy. Homepage, API health and
proxied API health returned 200; an anonymous university-scan POST returned 401.
A live scan inside the production API container returned 10 unique matching ISTA
citations from five pages in 10 seconds with no warnings. No production auth
bypass was enabled; this smoke check invoked the crawler service directly.
The next user step is to check/restore the configured Supabase project (or update
its settings if replaced), then sign in and use Discover → Search university
websites at http://localhost:3000. Docker is already running the updated images.


## 2026-10-10 — Student research workspace

### What was built and why

Discover and Find Professors now preserve queries, received results, filters and
selections across section navigation. Website/academic modes simplify the first
choice; optional guided outreach is collapsed. Returned authors are grouped by
shared paper, with individual evidence review and outreach. University selection
is automatic with India/international/both; seven reviewed sources replace four.
Live progress shows elapsed seconds, counts and a two-minute maximum rather than
an invented countdown. No new dependencies or database migration were required.

### Concepts and data flow

TanStack Query owns shared state above route components. A search updates this
cache even after its page unmounts. AbortControllers belong to the account
provider, so navigation keeps requests alive and cancel/sign-out stops them.
Zod validates tab-local sessionStorage snapshots. On reload, unfinished requests
become interrupted instead of displaying fake progress. Account changes recreate
the cache and remove the other account's snapshots. These snapshots can include
profile-derived matching inputs and guided draft text; they exclude credentials
and raw resume uploads. This is convenience storage, not cross-device history.

Forms use React Hook Form subscriptions to synchronize inputs. Coauthor groups
use stable supporting-paper IDs and only include authors in returned candidates.
The backend selects reviewed sources by region before the existing bounded,
robots-aware crawl. Program status, work mode and source limitations retain their
source evidence; IISc's department-specific fellowship is not labelled as a
currently open institute-wide opportunity.

### Important files

- Web: src/features/discovery/research-session.tsx, discovery-workspace.tsx,
  live-paper-discovery.tsx, university-discovery.tsx and university-contracts.ts.
- Web: src/features/mentors/live-mentor-discovery.tsx, paper-author-groups.tsx,
  features/workflow/use-workflow.ts, workflow-panel.tsx and
  features/outreach/live-outreach-workspace.tsx.
- Web integration: app/app-providers.tsx, discover/page.tsx, mentors/page.tsx,
  config/navigation.ts, API client/contracts, unit tests and e2e/account-journey.spec.ts.
- API: schemas/university.py, services/university_sources.py, university_scan.py,
  university_extraction.py, tests/test_university.py and generated OpenAPI.
- Documentation: README.md, PROJECT_SPEC.md, ROADMAP.md and the execution plan.

### Running and debugging

From the Desktop project use `docker compose up --build -d`, then localhost:3000.
Frontend checks: `npm run lint`, `npm run typecheck`, `npm run test`,
`npm run api:check`, `npm run test:e2e` in apps/web. Browser tests build production
assets and use isolated test identities/provider fixtures. API checks in apps/api:
`uv run ruff check .`, `uv run mypy app`, `uv run pytest`.

A null selection means intentionally no researcher selected; only undefined
should fall back to the initial value. Nullish coalescing caused mobile Back to
reselect the first researcher. Query cache notifications are asynchronous: tests
must wait for visible state, and keyboard focus must run after React commits the
new list/detail view. Refreshing guided generation now reports interruption;
it does not assume the backend is still waiting for another resume request.

### Live evidence and limitations

A real all-regions machine-learning scan found 10 citations in 26 seconds from
15 readable pages / 18 attempts. The IITK canonical SURGE page was reachable;
IISc correctly showed closed with a March 31, 2026 deadline. IITGN returned 403;
an EPFL research page was skipped because robots policy could not be verified.
The 10 citations were from ISTA: this is not proof of university diversity or
measured retrieval relevance. HTML citation context can be broad and titles may
remain unknown. Added sources can improve coverage but cannot guarantee results.

Coauthor groups only cover returned API candidates; website citations without
verified author metadata are not attached to guessed people. Refresh stops active
requests, and closing the tab ends its session storage. Save researcher is a
session-local marker. Disabled/full storage falls back to in-memory retention.
No emails are sent. Supabase was resumed and its public endpoints were reachable
in the preceding check; earlier log entries about unresolved DNS are historical.
Real user credentials were not used in automated tests.

Next: after Docker validation, refresh localhost:3000, run a search, switch to
Find Professors and return to Discover, then inspect grouped authors and sources.


### Automated validation

Frontend ESLint, TypeScript, generated API client check and production build
passed. All 61 unit/component tests and all 12 Chrome browser tests passed,
including mobile focus, navigation/reload retention, and an active website scan
finishing while another page is open. University browser responses use explicit
fixtures; the independent live scan above used real websites. Backend Ruff and
mypy (107 source files) passed; all 125 backend tests passed. The known Next.js
multiple-lockfile/standalone development-runner warnings do not fail the build;
Docker starts the standalone server directly. Unrelated existing work is preserved.

Docker rollout completed: both images built, all four services healthy. Homepage,
API health and proxied health returned HTTP 200; anonymous scan returned 401.
The Desktop project is now running the updated UI at http://localhost:3000.
Final diff whitespace check passed. No blanket commit was made because the
working tree also contains earlier, unrelated uncommitted work.


## 2026-10-10 - Public professor emails and worldwide university discovery

### What and why
Added a Find public email panel for a selected paper-backed researcher. A public
address is useful for outreach only when there is evidence that it belongs to the
selected person. Expanded the seven reviewed starting universities with relevant
institutions worldwide; there is no longer a seven-university domain ceiling.

### Concepts and data flow
Paper search -> persisted authors, affiliations, ROR IDs and publications -> ROR
v2 official-domain resolution -> per-request domain allowlist -> robots-aware,
DNS-pinned public HTTPS extraction -> deterministic identity corroboration ->
public contact evidence cache -> copyable address with source and check date.
The crawler requires a name in a personal-page heading/title and matching ORCID
or a stored publication. It reads published mailto, plain and explicit obfuscated
addresses, rejects generic/ambiguous contacts and never constructs an address.

Website scans use OpenAlex paper affiliations to choose up to six additional
institutions, then extract publications and program information from official
HTML. Region filters apply before selection. The UI lists selected institutions
and registry evidence. A university homepage is not itself an internship call.
Elapsed progress has a maximum budget, not a promise of an exact completion time.

### Important files
- apps/api/app/clients/institutions.py: ROR validation, bounded retries and cache.
- apps/api/app/services/institution_discovery.py: topic/region source selection.
- apps/api/app/services/contact.py and contact_extraction.py: controlled lookup,
  identity evidence, ambiguity handling and cancellation.
- apps/api/app/repositories/contact.py and db/models/contact.py: public evidence.
- apps/api/alembic/versions/20261010_0005_public_contacts.py: additive table migration.
- apps/api/app/api/v1/routes/contact.py and university.py: authenticated endpoints.
- apps/web/src/features/mentors/public-email-lookup.tsx: lookup/copy/evidence UI.
- apps/web/src/features/discovery/university-discovery.tsx: worldwide source display.
- Tests: apps/api/tests/test_contact.py, test_institutions.py, test_university.py;
  frontend contact/university tests and e2e/account-journey.spec.ts.
- PROJECT_SPEC.md, ROADMAP.md, README.md and docs/plans/professor-public-email.md
  document the approved scope. Generated OpenAPI/TypeScript contracts were refreshed.

### Run and test
From the project root: docker compose up -d --build. Docker runs migrations before
the API starts. Open localhost:3000, search Find Professors, select a researcher,
then Find public email. Discover -> university websites runs worldwide selection.
Backend: uv run ruff check ., uv run mypy app, uv run pytest (inside apps/api).
Frontend: npm --prefix apps/web run lint/typecheck/test/test:e2e, separately.
The E2E command performs a production build and uses isolated test identities.

### Debugging and limitations
A blocked page, missing ROR ID, registry outage, name initials, no corroborating
publication, unusual staff-ID mailbox, JavaScript-only page or PDF-only contact
may prevent a match. Use an exact official profile URL or review source links.
No paid provider or new dependency was added. Registry names/domains are trusted
metadata; webpage instructions are not executed. Registry active status is not an
internship opening. Researcher roles, availability, funding, external eligibility
and work mode remain unknown unless independently supported.

Scans remain bounded: six additional institutions, 40 pages and 120 seconds;
email lookup: six institutional records, 20 pages and 90 seconds. Page/time limits
can return fewer than 10/20/30 requested papers. Email cache lasts seven days for
found evidence and one hour for negative results; explicit recheck bypasses it.
This validates published identity evidence, not inbox deliverability. Public
contact evidence is shared catalog data; student profiles/drafts remain private.
There is no sending action. Browser tests mock remote sources; live observations
are separate: ROR returned MIT and official mit.edu domains, and an IIT Kanpur
profile lookup found published addresses corroborated by a stored paper title.

### Next step
Try your actual research topic in the refreshed Docker app, inspect selected
universities, then verify and copy a professor's sourced email. Broader recall
measurement and durable background jobs remain later work.

### Release verification
Backend Ruff and mypy passed; all 153 backend tests passed. Frontend ESLint,
TypeScript, API contract check and 64 unit tests passed. All 13 Playwright browser
tests passed, including the production build. Docker images rebuilt and all four
services became healthy. Web/API health returned 200; unauthenticated email and
university-scan endpoints returned 401. No user data reset or emails sent.


## 2026-10-10 - Login profile clock diagnosis
Observed profile 401 responses despite a signed-in browser. Added non-sensitive
verification reason logging in apps/api/app/auth/supabase.py: exception type only,
never token contents or user claims. Browser Retry profile reproduced
ImmatureSignatureError. Supabase JWKS was reachable and advertised ES256.
Container/Windows UTC was 2026-10-10 17:27 while the provider HTTP Date was
2026-10-11 06:55, about 48,505 seconds ahead. JWT issued-at checks therefore reject
fresh tokens before private profile retrieval. This is a clock problem, not a
missing profile. No validation was disabled and no time leeway was increased.

Data flow: browser session -> bearer token -> signature/issuer/audience/time
validation -> owner lookup -> private profile. The request fails at time validation.
Plan: docs/plans/phase-15-saas-foundations.md. Diagnostic commands: Docker API logs,
public JWKS response status/algorithms/Date, Windows UTC, w32tm /resync.
Windows Time service is stopped; starting it failed because this process cannot
open/control the service. Owner must enable automatic time and Sync now in Windows
Settings (administrator access may be needed), then sign in again and Retry profile.
Live profile success remains unverified until the system clock is corrected.


2026-10-11 live verification: after the owner synchronized Windows time, the provider/container clock difference fell to approximately 33 seconds. The existing signed-in browser successfully loaded /profile with the saved form and Profile is up to date. No profile edits or authentication relaxation were needed. The login/profile incident is resolved.


## 2026-10-11 - Connected research workspace (phase 1 implementation)

Built account-owned saved papers, collections, reading notes and author shortlists;
added paper details with grouped authors, exact paper/author handoff, recipient
selection with provenance/version checking, and draft restoration in Conversations.
Academic search is the default; UI paper targets are 10, 20 or 30. University DOI
citations can resolve only after an exact identifier match; unresolvable citations
remain evidence, not verified authors. No new dependencies were introduced.

Why: students should not repeat searches or lose the paper that motivated outreach.
Data flow: OpenAlex -> persisted catalog -> selected paper/author IDs -> owner-scoped
research service -> grounded draft -> saved recipient and versioned draft editor.
Concepts: foreign keys, account ownership, additive migrations, optimistic version
checks, provenance, contract validation and persistent server state via TanStack Query.

Important files: app/repositories/research.py, app/services/research.py,
app/api/v1/routes/research.py, app/db/models/research.py under apps/api;
apps/api/alembic/versions/20261011_0006_research_workspace.py;
apps/web/src/features/research and apps/web/src/lib/api/research.ts.

Validation so far: backend full suite 154 passed; Ruff/mypy passed; frontend 64 unit
tests passed. The new browser journey found a timezone-free SQLite timestamp that
failed the frontend contract; normalizing stored UTC timestamps fixes it and has a
backend regression assertion. Browser retest of that exact journey passed. A separate
guided checkbox test was intermittent; the full suite is being rerun.
Commands: uv run ruff check ., uv run mypy app, uv run pytest (apps/api);
npm --prefix apps/web run lint/typecheck/test/test:e2e from the project root.
The E2E runner owns fixture data and an isolated database; it sends no real email.

Limitations: migration must be applied to the running PostgreSQL service before use;
Gmail and PDF reading are not implemented; arXiv-only website citation resolution
is not implemented. Research/draft lists currently return the latest 200 records.
No credentials or private data were added to source. Google setup guide:
docs/GMAIL_SETUP.md. Next step: finish phase-one checks, then private PDF processing
and page-cited retrieval with explicit unsupported-document states.


Validation update: all 14 Playwright tests now pass, including the new exact-author
handoff and saved notes. Fixed controlled-input timing with useSyncExternalStore;
the existing null-selection regression test caught and verified a correction to
preserve intentionally cleared selections. All 64 frontend tests pass; lint,
production build, backend Ruff and mypy pass. Docker rebuilt and all four services
are healthy. Migration 20261011_0006 applied to PostgreSQL. A rollback-only database
check passed research persistence, owner filtering, timezone serialization and
owner-deletion cascade; no test records were committed. The full backend suite
previously passed 154 tests, and the changed timestamp regression passed separately.
Remaining phase-one edge: arXiv-only university citation resolution. DOI resolution
is implemented. Full-paper reading and Gmail remain subsequent work, not current
capabilities. The requested Google Cloud preparation guide is now available.


## 2026-10-11 - Early email availability on Discover

Built: academic results start a bounded background contact pass, show public email
availability and source links on paper cards, and provide an optional contactable-
author filter. Direct Contact links retain exact paper and author IDs. Detailed
contact views reuse the same evidence. No new dependency or database schema.

Why: a student should know whether a public address was found before investing
in opening a paper and preparing outreach. Failure and unchecked states stay
separate from completed negative searches; every paper stays visible by default.

Concepts/data flow: papers -> corresponding-first, breadth-first deduplicated queue
-> two concurrent authenticated lookups -> existing official-site evidence/cache
-> account-scoped research state -> paper cards and author detail. The first pass
checks six authors maximum; further authors retain manual lookup. Cancellation,
refresh interruption and explicit retry use the existing research task lifecycle.

Important files: apps/web/src/features/discovery/early-contacts.tsx and its test;
live-paper-discovery.tsx; apps/web/e2e/account-journey.spec.ts. Specification and
execution plan describe the bounded scope. Run npm --prefix apps/web run lint,
typecheck, test and test:e2e from the repository root (separate commands).

Debugging: a rate limit or blocked official site means incomplete lookup, not an
absent address. A refresh interrupts requests; resume explicitly. Backend caching
avoids repeated crawling; source timestamps remain visible in author details.
Limitations: six authors per pass, approximately five minutes worst-case at the
90-second per-lookup budget, no guarantee of email deliverability, professor role,
or internship availability. University citations still need catalog resolution.
No Gmail sending, durable offline jobs or visual redesign in this increment.
Validation: ESLint and TypeScript passed, all 68 unit tests passed, and all 15
Playwright flows passed with the production build. Contact responses in browser
tests are fixtures; no real university crawling or emails occurred. Docker Desktop
was stopped and has been started. After one transient Docker Hub timeout, the
web image rebuilt successfully and all four Docker services became healthy.
Next: complete this increment's browser validation and local Docker refresh, then
finish phase-one citation resolution before the PDF reading workspace.


## 2026-10-11 - arXiv website-citation resolution
Built strict recognition of official arXiv abstract/PDF URLs, including legacy
identifiers and revision suffixes. Uses arXiv's documented canonical DOI mapping
and the existing authenticated academic search. Only an exact returned DOI enables
the saved-paper/author workflow; title similarity cannot verify authorship.
Resolution state now survives navigation in the account-scoped research session.

Why: university pages often link preprints instead of supplying publication DOIs.
Data flow: extracted publication URL -> validated arXiv ID -> canonical DOI ->
OpenAlex retrieval/persistence -> exact DOI check -> catalog paper and author IDs.
Concepts: identifier normalization, canonical versus version-specific references,
identity evidence, negative matches and cached UI state. No new dependencies.
Important files: apps/web/src/features/research/citation-identifier.ts,
resolve-citation.tsx, their tests, and discovery/university-discovery.tsx.
Run frontend lint, typecheck, test and test:e2e. Tests cover versioned/legacy IDs,
lookalike hosts, malformed links, DOI prefixes and unrelated provider results.
Limitations: OpenAlex may not index the canonical preprint DOI or may merge it
into a journal work with a different DOI; that remains explicitly unresolved.
The DOI identifies the canonical paper, not a specific revision. Source link stays
visible. No title-based fallback, provider-authorship guessing or paywall bypass.
Reference: https://info.arxiv.org/help/doi.html.
Next: verify this increment, then private PDF ingestion and page-cited retrieval.

Citation validation: 81 frontend tests and 15 browser flows passed; lint, typecheck,
production and Docker builds passed. All four local Docker services are healthy.
The provider resolution tests use fixtures; no claim of complete arXiv coverage.


## 2026-10-12 - Private PDF ingestion foundation (phase 2 in progress)

Built an explicit scan-before-parse interface, ClamAV INSTREAM client, isolated
PDF parsing process, resource bounds, numbered pages and within-page chunks with
exact offsets. Added pypdf 6.20.0 for text extraction; no OCR or model dependency.
The child process limits CPU/memory on Linux and wall time on all platforms.
Cancellation kills/reaps the parser. Unavailable scanning fails closed.

Why: source-backed answers need reliable page provenance, and uploaded PDFs must
not run unbounded inside the API. Flow: bounded PDF bytes -> clean antivirus verdict
-> isolated parser -> validated status/pages/chunks. No text reaches an AI service.
Unknown/unsupported content never becomes generated evidence. Statuses separate
ready, unsupported, scan-rejected and processing-failed results.

Important files: apps/api/app/documents/contracts.py, scanner.py, processing.py,
pdf_worker.py; apps/api/tests/test_pdf_processing.py; pyproject.toml and uv.lock.
Concepts: process isolation, bounded parsing, fail-closed dependencies, typed
processing outcomes and source offsets. Setup: docs/PRIVATE_PDF_SETUP.md.

Validation: backend Ruff and mypy passed; full suite passed 167 tests before the
last two cancellation cases were added. Final focused suite passed all 15 tests.
Commands: uv run ruff check ., uv run mypy app, uv run pytest; targeted:
uv run pytest tests/test_pdf_processing.py -q. Fixtures are generated locally.
ClamAV protocol tests use an owned loopback stub; a real signature database has
not been tested. A test-harness issue with long binary parameter IDs on Windows
was fixed by assigning short names; fixture contents are not test identifiers.

Limitations: no upload endpoint, private storage adapter, persisted document/job
schema, reader UI, pgvector/FTS or cited question answering yet. Supabase storage
credentials and a scanner host are absent. Windows enforces wall time only; the
production Linux parser also caps CPU and virtual memory. Complex layouts and
image-only pages are not interpreted. PDF phase is NOT complete.
Next: private storage and owner-scoped document/page/job records with worker leases,
then the upload/reader UI and evaluated page-cited retrieval.

Linux verification: a generated text PDF passed the resource-limited subprocess
in the rebuilt API image (fixture scanner only). Docker services refreshed and
became healthy. This does not verify real antivirus signatures or enable uploads.


## 2026-10-12 — Durable PDF document records and processing claims
Built owner-scoped document records, numbered extracted pages/chunks and saved
processing jobs. These let processing survive process restarts rather than relying
on an in-memory task. No new dependency was needed for this increment.

Concepts: transactions, conditional state updates, PostgreSQL SKIP LOCKED,
leases, fencing tokens, retry backoff and foreign-key cascades. A worker claims
one job, commits the claim, processes outside the transaction, then publishes only
if its token is current and unexpired. An expired worker cannot overwrite a later
attempt. Transient failures retry after 30/60 seconds; three failures or crashes
exhaust the job. Unsupported documents are terminal rather than endlessly retried.
Only the owner can read pages, and only after processing reaches ready.

Files: apps/api/app/db/models/documents.py and models/__init__.py;
alembic/versions/20261012_0007_private_documents.py;
app/documents/repository.py; tests/test_document_repository.py.
Run from apps/api: uv run ruff check .; uv run mypy app;
uv run pytest -q; focused: uv run pytest tests/test_document_repository.py -q.
Results: Ruff clean, mypy 127 files clean, full suite 174 passed. The five new
regressions cover ownership/quarantine, duplicate enqueue, persisted restart,
stale completions, bounded transient/crash retries, unsupported PDFs and cascade
deletion. SQLite tests exercise upgrade/downgrade; a local PostgreSQL smoke test
also checked actual concurrent SKIP LOCKED, fencing and page persistence. Temporary
PostgreSQL fixtures were removed. API rebuilt and migration applied via Docker;
all four services are healthy.

Debugging: a job can remain processing until its five-minute claim expires after
a crash. Inspect status/attempts/last_error without logging PDF text. Finalization
returning false means the claim is stale; do not force-write results. Callers must
commit claims before external work and commit completion afterward.

Limitations: this is persistence, not a running upload pipeline. DB cascades do not
remove Storage objects. Storage transport, durable blob cleanup, worker loop and
upload endpoints are still pending, as are the reader and cited retrieval. Real
ClamAV and private Storage credentials remain unconfigured. No UI or API contract
changed, so frontend tests were not repeated for this increment.
Next: private Supabase storage and deletion cleanup, then connect the scanner and
parser through a worker before enabling authorized document uploads.


## 2026-10-15 — Private PDF storage, durable uploads and cleanup worker
Built the Supabase storage adapter and a worker connecting durable jobs to hash
verification, antivirus scanning and isolated extraction. Added an upload service
that records a document and cleanup intent before writing external bytes. This
avoids losing track of a file when upload confirmation or the API process fails.
No new dependencies: uses existing HTTPX2, SQLAlchemy and Python asyncio/hashlib.

Concepts: durable intent, eventual deletion, transaction boundaries, row locking,
checksums, fail-closed private storage and bounded retry queues. Upload flow:
validate input -> lock owner/check quotas -> commit document/blob ledger -> upload
private object -> enqueue processing -> claim/commit -> download/hash/scan/parse ->
publish pages only with a current claim token. Account deletion cascades document
records; the independent blob ledger remains until external deletion succeeds.
A 15-minute grace protects active uploads, and abandoned uploads become failed.
Cleanup has fenced five-minute claims, ten attempts and exponential backoff;
exhausted cleanup records remain visible rather than being silently discarded.

Important files under apps/api: app/documents/storage.py, blobs.py, service.py,
worker.py, repository.py; app/db/models/documents.py and models/__init__.py;
app/core/config.py; alembic/versions/20261012_0008_document_blob_cleanup.py;
tests/test_document_storage.py, test_document_worker.py, test_document_service.py.
Server settings documented in apps/api/.env.example and docs/PRIVATE_PDF_SETUP.md.

Run from apps/api: uv run ruff check .; uv run mypy app; uv run pytest -q.
Results: lint passes, mypy passes for 131 files, 194 backend tests passed. Twenty
new tests cover private-bucket verification, redirects, safe errors, bounded
responses, rate limits, owner isolation, committed upload intent, failed uploads,
actual fixture-PDF extraction, unavailable scanner, byte mismatch, cancellation,
cleanup grace, stale claims, deletion retries and account-deletion cascades.
No frontend contract/UI changed, so frontend gates were not repeated.

A test exposed naive SQLite timestamps being compared to UTC Python timestamps
in ORM update synchronization. The abandoned-upload update now uses database
matching with synchronize_session=fetch rather than evaluating dates in Python.

Debugging: --status prints aggregate processing/cleanup state without document
contents. --once handles at most one item of each queue. No configured storage key
or scanner host means the worker refuses to start. Rate limits preserve a bounded
retry delay; failed cleanup needs operator attention after fixing the underlying
service. Never remove a cleanup ledger row just to clear its failed status.

Limitations: no HTTP upload/reader UI yet; no cited Q&A yet. Storage and scanner
validation is fixture-based, not a live-service claim. Default Compose does not
start an antivirus or continuous worker. Windows parser limits differ from Linux;
use the Linux container for production. Physical account-file deletion is eventual
and depends on a running worker and reachable Storage. Original files remain
unavailable through the app until authorized ready-only access is implemented.
Next: wire authenticated upload/status/delete and ready-only file access, then
implement the student reading workspace and evaluated page-cited retrieval.

Local validation completed: API image rebuilt; migration 20261012_0008 applied.
PostgreSQL smoke verified AccountDeletionService cascades while retaining cleanup
intent, concurrent SKIP LOCKED behavior, expired-claim recovery and stale completion
rejection. Temporary fixtures removed; worker --status reports empty queues.
All four Docker services healthy. This did not contact live Storage or antivirus.


## 2026-10-15 — Authenticated PDF endpoints and paper workspace controls
Built upload/list/status/delete and ready-only extracted-page APIs, plus paper
workspace upload forms, status polling, removal and a numbered text preview.
This connects the previously tested processing foundation to the student journey.
No new dependency or migration was required. Private storage and scanner validation
remain necessary before setting DOCUMENT_UPLOADS_ENABLED=true.

Concepts: authenticated transport, bounded request streaming, persisted throttling,
private response caching, schema-checked client requests and background status polling.
Flow: signed-in student chooses a PDF -> bounded raw-body API -> durable upload
service -> independent worker -> database status/pages -> polling UI -> text preview.
The API commits a newly authenticated owner before opening the upload service's
independent transaction. Ownership checks apply to status, pages and deletion;
ready-only pages use private/no-store headers. Five upload intents per minute per
owner are counted in the cleanup ledger, including failed or deleted attempts.
Files are student-provided; association does not verify their academic identity.

Files: apps/api/app/api/v1/routes/documents.py and router.py;
app/documents/service.py; app/core/config.py; tests/test_document_api.py;
apps/web/src/lib/api/documents.ts; features/research/paper-documents.tsx and its
tests; paper-workspace.tsx; e2e/account-journey.spec.ts; generated API contracts.
Configuration and setup guidance updated in apps/api/.env.example and
this repository's docs/PRIVATE_PDF_SETUP.md.

Validation: uv run ruff check . and uv run mypy app pass (132 files); complete
backend suite 197 passed. Frontend lint/types pass, 84 unit tests pass, generated
contracts match, production build succeeds and all 16 Playwright flows pass.
The final upload-refresh refinement also passed its three focused component tests.
Browser tests include disabled setup, fixture page switching, accessibility and
390px mobile overflow checks. Backend tests cover an uploaded fixture through
worker extraction, cross-account read/delete denial, quarantine, upload size/type,
authentication, disabled configuration and five-intent throttling. Real Storage
and antivirus are not used by these tests. No email is sent.

Debugging: HTTP 202 means queued, not scanned. A pending status requires a running
worker; navigation does not stop that worker. 503 setup-disabled means the explicit
flag or required service settings are missing. Unsupported/rejected documents have
no readable-page access. File deletion hides database records immediately and queues
physical cleanup. Status refresh also runs after failed upload responses.
The initial browser test used an exact label-text locator that included select
options; using the accessible combobox role fixed the test without bypassing UI.

Limitations: extracted text preview is not the original-layout PDF reader; formulas,
tables and columns may lose layout. No cited Q&A or automatic open-access PDF fetch
yet. Uploads stay off until live services are validated. Next: original PDF access,
then PostgreSQL FTS/pgvector retrieval with measured page-citation quality.

Local API and web images rebuilt and refreshed; all four Docker services passed
health checks. Live OpenAPI includes the document routes. Upload enablement remains
off. Docker dependency installation reported 14 audit findings (3 moderate,
10 high, 1 critical); impact/production reachability was not evaluated in this
increment and needs dependency triage before public launch. No forced upgrades.


### Original PDF access (2026-10-15)
Added authenticated GET /documents/{id}/file for ready documents. The service
checks ownership before fetching, SHA-256 against the scanned bytes, and ownership
and readiness again after fetching. Responses use private/no-store caching and
defensive PDF headers. Storage failures return a safe 503; altered files return
409. No migration or dependency added. Original-reader UI integration, open-access
fetching and cited retrieval remain pending; uploads remain disabled by default.

Why: extracted text loses paper layout; protected original access is a prerequisite
for the side-by-side reader. Concepts: authorization before I/O, content integrity,
bounded external calls and rechecking state after network waits. Data flow: bearer
identity -> owned ready record -> private blob -> SHA-256 -> fresh state check -> PDF.
Files: documents/service.py, api/v1/routes/documents.py, document API/service tests,
OpenAPI and generated frontend contracts. Backend Ruff/mypy pass; full pre-existing
197-test suite passes plus the new race/failure regression (4 service tests pass).
Run uv run pytest tests/test_document_api.py tests/test_document_service.py for this
slice. 409 means not ready or changed bytes; 503 means storage unavailable. Automated
storage remains a fixture; live Storage/ClamAV and browser original-PDF behavior are
not validated. This increment has not been deployed to Docker. Next: integrate
authorized original viewing into the reader, then evaluated page-cited retrieval.


### Original PDF reader integration (2026-10-15)
Ready PDFs now offer an explicit original-file viewer and download fallback alongside
extracted text. Bearer-authenticated fetch uses no-store; temporary blob URLs are
revoked on close/unmount, pending fetches abort, and query bytes expire immediately
after the reader unmounts. Account identity changes already remount the private
workspace. No dependency or migration added. Browser-native PDF support varies;
the sandboxed preview may require using the download fallback. Live uploads remain
disabled pending Storage/ClamAV validation. Cited Q&A and OA fetching remain pending.

Why: students can inspect figures/layout rather than rely solely on extracted text.
Concepts: authenticated binary transport, AbortSignal, TanStack Query lifecycle,
object-URL revocation and sandboxed rendering. Flow: View original PDF -> authenticated
ready-only endpoint -> in-memory Blob -> temporary viewer/download URL -> cleanup.
Files: lib/api/documents.ts, features/research/original-pdf.tsx and its tests,
paper-documents.tsx, e2e/account-journey.spec.ts. Tests: 87 frontend tests passed;
3 lifecycle tests passed again after the lint fix; frontend lint/typecheck and
production build passed. Fixed Windows source encoding by saving the new component
as UTF-8. Debugging: 409 means processing/integrity failure; 404 means unavailable;
Retry PDF handles temporary errors. No Storage/antivirus calls occur in fixtures.
This increment is not yet deployed to Docker. Next: evaluate page-aware retrieval
and add source-backed questions; live provider setup remains a separate prerequisite.

Reader validation complete: production build and all 16 Playwright flows passed,
including PDF failure/retry controls, extracted-text accessibility and mobile layout.
Full frontend lint and typecheck passed. Original PDF visual rendering with a real
scanned file remains unverified; fixture tests cover URL cleanup and cancellation.


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

Why: answer generation must start from verifiable source passages. Concepts:
full-text indexing, keyword normalization, bound SQL parameters, deterministic
ranking, citation offsets and evaluation separation by database engine. Flow:
authenticated query -> owned ready document -> page prefilter -> ranked chunks ->
exact-slice validation -> deduplicated excerpts. Important files: documents/retrieval.py,
routes/documents.py, migration 0009, test_document_retrieval.py and the opt-in
PostgreSQL test; generated OpenAPI/frontend contracts updated. Run backend Ruff,
mypy and pytest; frontend api:check and typecheck validate contracts. Debugging:
404 protects other accounts, 409 means processing is incomplete, no_matches is
expected for unsupported keywords; simple text search cannot handle synonyms.
See docs/PASSAGE_RETRIEVAL_EVALUATION.md for the small fixture evidence and limits.
Next: start Docker/apply migration and pass real PostgreSQL retrieval before
claiming that path validated; then add evaluated vector retrieval and cited answers.
No Docker deployment or public-release completion is claimed.


### Verified PostgreSQL retrieval and passage-search UI
PostgreSQL integration passed on a freshly migrated temporary database, including
GIN index presence, ready-state/ownership checks, exact page slices, all three
expected first-page matches and three no-match queries. Test database removed.
These remain tiny synthetic smoke tests, not general retrieval accuracy claims.
The extracted-text reader now offers keyword passage search, loading/error/no-match
states and keyboard-accessible source-page buttons. Excerpts remain plain text;
no AI answer is implied. No dependency or schema change beyond migration 0009.

Why: students need to inspect retrieved evidence before trusting generated answers.
Concepts: database-engine integration tests, disposable fixtures, controlled forms,
mutation state and source-page navigation. Data flow: typed keywords -> authenticated
passage endpoint -> safe excerpt list -> selected page plus keyboard focus.
Files: lib/api/documents.ts, passage-search.tsx and tests, paper-documents.tsx,
e2e/account-journey.spec.ts and retrieval evaluation documentation.
Validation so far: 90 frontend tests, lint and typecheck pass; PostgreSQL test
passes (1 integration test, 0.39 seconds; not a per-query latency measurement).
Use npm run test and npm run test:e2e; PostgreSQL setup is documented in the
evaluation file. Debugging: empty results may mean different wording, not absence
of information; searches require ready documents. Live Storage/scanning is still
unconfigured. Next: evaluated vector retrieval and source-backed answer generation.


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

Why: semantic search needs a reliable conversion from text to comparable numeric
vectors before database retrieval is added. Concepts: embedding model/version
compatibility, vector normalization, strict external-response validation, bounded
retry policies and cancellation propagation. Data flow: bounded passage batch ->
HTTP embedding request -> validated/reordered normalized vectors + token accounting.
Important files: app/documents/embeddings.py, tests/test_embeddings.py and
docs/SEMANTIC_RETRIEVAL.md. No SDK dependency was added; HTTPX and Pydantic already
exist. All tests use synthetic text and mocked HTTP; no paid requests or private
files were used. Run uv run ruff check ., uv run mypy app and uv run pytest.
Debugging: huge parametrized test values need short explicit IDs on Windows to
avoid path-length errors. Provider errors must remain sanitized. Next work must
add persisted quotas and owner-scoped vector records before connecting this adapter
to student requests; token metadata alone does not enforce a usage limit.

Embedding adapter validation: Ruff clean; mypy clean (134 files); full backend
suite 228 passed, 1 optional PostgreSQL test skipped because its URL was unset.
27 new embedding tests use HTTP fixtures. No frontend change, new schema, live
provider call or Docker deployment was needed for this unconnected adapter.


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

Why: embeddings must remain tied to the student's actual source text, and must be
deleted with it. Concepts: pgvector cosine distance, foreign-key cascades, atomic
replacement, source hashes and model compatibility. Ownership is derived through
page -> document -> account, avoiding redundant owner fields that could disagree.
Flow: validated chunks/vectors -> lock owned ready document -> validate complete
source coverage -> replace transactionally -> search within one owned document.
Important files: db/models/document_vectors.py, documents/vectors.py, migration
0010, test_document_vectors.py and test_document_retrieval_postgres.py, pyproject
and uv.lock. Run uv run ruff check ., uv run mypy app, uv run pytest. Set
TEST_DOCUMENT_POSTGRES_URL only to a disposable migrated database for the real
PostgreSQL test. The default suite deliberately skips that opt-in check.
Debugging: 409 rejects source/model/dimension mismatch; 503 means SQLite cannot
perform vector search. Keep failed replacements inside caller-managed rollback.
No HNSW approximation is needed for at most 2000 chunks per document initially.
Next: durable indexing jobs with account usage reservations and student disclosure,
then compare hybrid retrieval on representative labelled papers. This increment
is not deployed to the local app yet; its running schema remains at 0009.
Official integration reference: https://github.com/pgvector/pgvector-python#sqlalchemy

Vector increment final gates: Ruff clean, mypy clean (136 files), full suite
234 passed with 1 default opt-in PostgreSQL skip. The same PostgreSQL integration
test was explicitly run separately against a temporary pgvector database and
passed, including migration downgrade/reapply. No frontend/API contract changed.


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

Why: indexing involves external calls that may succeed even when a worker loses
its connection. We reserve budget before calls and keep it on uncertain outcomes
so retries cannot silently exceed the account limit. These are conservative budget
units, not an exact provider bill. Concepts: durable job state, unique enqueue,
SKIP LOCKED, lease fencing, quota serialization via owner locks and atomic writes.
Flow: accepted disclosure -> enqueue -> claim and reserve -> commit -> renew lease
and embed bounded batches -> validate -> commit vector replacement and completion.
Cancellation leaves a recoverable lease and charged reservation. Midnight renewal
requires a fresh daily reservation. Failed/completed jobs currently do not expose a
manual reindex action; that belongs with the upcoming API/state design.
Files: db/models/indexing.py, migration 0011, documents/indexing.py,
documents/index_worker.py, test_document_indexing.py and PostgreSQL integration test.
Run uv run pytest tests/test_document_indexing.py -q; opt-in PostgreSQL uses
TEST_DOCUMENT_POSTGRES_URL on a disposable migrated database. Six lifecycle/worker
tests passed, plus PostgreSQL retrieval/vector/indexing checks and downgrade/reapply.
Debugging: stale workers return without writing; daily_quota means wait for UTC reset;
document_exceeds_quota requires a smaller document or an operator-adjusted limit.
A cached ORM object can survive a database cascade in the session identity map: tests
verify deletion with a fresh SELECT, not a cached get(). No new dependency added.
Next: expose owner-scoped indexing status/consent controls and worker configuration,
then connect hybrid retrieval and evaluate cited answers. Migration 0011 is not
applied to the running local app; this increment remains an unexposed backend service.

Final indexing gates: Ruff clean, mypy clean (139 files), backend suite 240 passed
with one default opt-in PostgreSQL skip. That integration test passed separately
on temporary PostgreSQL, including 0011 downgrade/reapply. No frontend contract
change or live provider call. Multi-connection quota contention stress testing
remains part of worker rollout; current integration validates sequential lifecycle.


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

Learning notes: consent binds an explicit student action to a disclosure version;
lease fencing prevents cancelled/stale workers from saving results. Flow: reader
loads private status -> student accepts disclosure -> API checks ownership and
queues one job -> worker reserves usage before provider I/O -> validated vectors
commit atomically. Polling shows progress without sending text automatically.
Important files: app/api/v1/routes/documents.py, app/documents/indexing.py,
app/documents/index_worker.py, src/features/research/document-indexing.tsx,
src/lib/api/documents.ts, and their tests. See docs/SEMANTIC_RETRIEVAL.md for setup.
Run indexing tests from apps/api with uv run pytest tests/test_document_indexing.py.
Use docker compose up -d --wait from the project root to run the local app.
If Docker's engine pipe is unavailable, start Docker Desktop before retrying.
A setup-disabled message is expected until configuration is complete; queued jobs
need a running worker. A successful index is not yet a working paper-chat feature.


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

Why: exact keywords and semantic similarity find different useful passages. Rank
fusion combines their ordering without pretending incomparable raw scores are
probabilities. Flow: owner/readiness check -> keyword retrieval + vector retrieval
-> reload source pages -> fuse valid candidates -> suppress overlapping citations.
Important files: apps/api/app/documents/hybrid.py,
apps/api/tests/test_document_hybrid.py, apps/api/tests/test_document_vectors.py.
Run: uv run pytest tests/test_document_hybrid.py from apps/api. PostgreSQL integration
uses TEST_DOCUMENT_POSTGRES_URL and tests/test_document_retrieval_postgres.py.
Debug: a 404 may indicate an ownership mismatch; 409 means a paper is not ready;
503 from vector search means PostgreSQL is required. Empty candidates are not proof
of absence of an answer. There is no student-facing hybrid endpoint yet, so the
existing UI still offers keyword passage search. Fixed fusion weights are a baseline,
not tuned parameters. No live provider calls or private documents used in tests.


Hybrid increment final validation: Ruff passed; mypy passed for 140 source files;
full backend suite passed 245 tests with one opt-in PostgreSQL skip. That PostgreSQL
integration test passed separately against a disposable local database using actual
FTS and pgvector. Formatting and diff checks passed. Frontend was unchanged, so no
frontend gates were repeated. This internal service is not exposed to students yet.


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

Concept: a database transaction must durably reserve an external call's allowance
before the call starts. Rolling usage back after a timeout could allow unbounded
spending even though the provider processed the request. Holding a database lock
across HTTP would instead block other work. This service commits, releases its
session, embeds the question, then opens a new session for private retrieval.
Files: apps/api/app/documents/semantic.py; tests/test_document_semantic.py;
tests/test_document_retrieval_postgres.py. Run from apps/api with
uv run pytest tests/test_document_semantic.py; opt-in PostgreSQL uses
TEST_DOCUMENT_POSTGRES_URL. A paper_index_required error means indexing must finish;
embedding_daily_quota resets at midnight UTC. A provider error keeps the allowance.
The user-facing keyword search is unchanged until the next API/UI integration.


Query-service final gates: 250 backend tests passed with one opt-in PostgreSQL
skip; that integration test passed separately on PostgreSQL with fixture embeddings,
including cancellation and invalid-vector usage retention. Ruff, formatting and
mypy (141 source files) passed. No frontend contracts changed, so frontend gates
were not repeated. Phase 2 remains active; no semantic endpoint deployed yet.


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

Concepts: transport routes validate schemas and translate provider errors; the query
service handles quota transactions and retrieval. React Hook Form validates input;
TanStack mutations keep search results local and prevent resubmission while pending.
Flow: completed index -> explicit question-sharing consent -> authenticated POST ->
committed quota reservation -> embedding -> private hybrid passages -> source page.
Important files: apps/api/app/api/v1/routes/documents.py;
apps/web/src/features/research/passage-search.tsx, document-indexing.tsx,
paper-documents.tsx; apps/web/src/lib/api/documents.ts; generated API contracts;
tests/test_document_api.py, passage-search.test.tsx and e2e/account-journey.spec.ts.
Run backend pytest/Ruff/mypy and frontend lint/typecheck/test/test:e2e/api:check.
Debug: missing semantic form means indexing is disabled or incomplete. A 429 means
the daily budget is reserved; a 503 means setup/provider availability needs attention.
Use keyword search while resolving either. Tests use fixture providers/results;
real scientific retrieval quality and generated-answer support remain unmeasured.


Semantic API/reader validation: backend Ruff and mypy passed (141 files); pytest
250 passed, one opt-in PostgreSQL skip (service integration passed separately in
the previous increment). Frontend lint/typecheck passed; 94 unit tests passed;
generated contract check passed; production build and all 16 Playwright flows
passed, including unchecked consent, zero pre-consent calls, exact request payload,
source-page navigation, accessibility and mobile overflow checks. No live AI calls.

Local deployment: Docker API/web builds passed and compose up --wait completed; all four services healthy. Semantic setup remains disabled by default. No live provider calls made.


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

Why: a benchmark should distinguish finding relevant passages from producing a
supported answer. Recall measures relevant evidence recovered; MRR measures how
soon the first valid relevant passage appears; nDCG rewards useful evidence near
the top. Invalid citations and duplicate results must not inflate these scores.
Data flow: local JSON -> schema/reference validation -> per-query gains -> macro
metrics and separate unsupported-query rate -> JSON report. No network involved.
Important files: apps/api/app/documents/evaluation.py;
apps/api/scripts/evaluate_paper_passages.py;
apps/api/evaluation/passage-metric-sanity-v1.json;
apps/api/tests/test_passage_evaluation.py.
Run from apps/api: uv run python -m scripts.evaluate_paper_passages
 evaluation/passage-metric-sanity-v1.json (one command, on one line).
Run focused tests: uv run pytest tests/test_passage_evaluation.py.
Debug: incomplete engine coverage fails validation; record an empty result for a
completed no-match query, but never disguise a failed request as a no-match. Audit
citations against exact stored slices before exporting citation_valid. Report corpus,
label method, failures and environment alongside actual latency observations.


Evaluation-tooling gates: Ruff passed, mypy passed (142 source files), full backend
suite passed 258 tests with one opt-in PostgreSQL skip. Two further metric edge
cases were added after full-suite collection; the complete focused evaluator suite
passed all 10 tests. CLI execution produced the expected synthetic arithmetic.
Frontend and database behavior were unchanged; no frontend rebuild or deployment
was required. Real-paper evaluation is still pending, not claimed complete.


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

Built: an offline public-PDF pilot runner, frozen provisional labels and measured
raw rankings/report. Why: synthetic arithmetic tests cannot reveal actual retrieval
failure modes. Concepts: frozen evidence labels, extraction fingerprints, retrieval
versus answer support, isolated fixture transactions, and small-sample limitations.
Flow: verify local PDF hash -> extract and verify page hashes -> create isolated
owner/document/page records -> production FTS -> exact-slice citation audit ->
metric report -> roll back fixture rows. No app upload/scanning path was changed.
Files: apps/api/scripts/run_public_paper_pilot.py;
apps/api/evaluation/scikit-learn-public-pilot-v1.json;
apps/api/evaluation/scikit-learn-public-pilot-results-v1.json;
apps/api/tests/test_public_paper_pilot.py.
Run from apps/api with a migrated disposable TEST_DOCUMENT_POSTGRES_URL:
uv run python -m scripts.run_public_paper_pilot PATH_TO_PUBLISHER_PDF
The PDF URL/hash are in the manifest. A mismatched PDF or changed extraction fails
before measurement; review labels rather than silently accepting new offsets.
The ignored .test-tmp-public-papers cache contains only the public source PDF.
Tests cover PDF-hash mismatch and extraction drift; the actual PostgreSQL pilot
completed with no failed queries. This is a development pilot, not a held-out
benchmark. Future retrieval changes must not be advertised using this small sample.


Public-pilot final validation: actual PostgreSQL pilot completed (six queries, no
failed requests); temporary database removed. Ruff/mypy passed. Full backend suite:
262 passed, one opt-in PostgreSQL skip. Focused pilot/evaluator tests: 12 passed.
A separate focused invocation initially hit a Windows default pytest temp-directory
permission error; rerunning with a project-local --basetemp passed. No production
behavior, API, schema or frontend change; no app rebuild required this increment.


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

Concept: independent papers often reuse page/offset IDs and query names. Namespacing
with encoded (dataset, identifier) pairs prevents accidental merging. Fair comparison
requires every engine to process every query across all papers. An empty result and
an omitted query must not be treated as equivalent.
Files: app/documents/evaluation.py; scripts/combine_paper_pilots.py;
evaluation/liblinear-public-pilot-v1.json; liblinear-public-pilot-results-v1.json;
public-two-paper-pilot-results-v1.json; tests/test_passage_evaluation.py (under apps/api).
Run from apps/api: uv run python -m scripts.combine_paper_pilots
 evaluation/scikit-learn-public-pilot-results-v1.json
 evaluation/liblinear-public-pilot-results-v1.json --name public-two-paper-pilot-v1
(join these lines into one command). No database/provider is needed to replay metrics.
The second raw run used the existing run_public_paper_pilot CLI with --manifest and
a disposable migrated PostgreSQL database; all fixture data/database were removed.
Missing provider configuration prevents live semantic measurements, but offline
aggregation and label review remain possible. Never paste API secrets into chat.


Two-paper final gates: Ruff and mypy passed; full backend suite 264 passed with one
opt-in PostgreSQL skip. Actual second-paper PostgreSQL retrieval completed separately
without failed queries, and its disposable database was removed. Aggregation CLI
exactly reproduces the saved combined report. No frontend/API/schema changes or
live AI requests. Server embedding key remains unconfigured; semantic comparison
is explicitly pending.


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

Learning notes:
- Embeddings are numerical representations for finding passages, not generated answers.
  Equal dimensions do not make vectors from different models comparable.
- Consent versioning prevents a configuration change from silently sharing data with
  a different company. Lease tokens fence off a worker whose approval has been replaced.
- Flow: reviewed paper consent -> durable job -> prefix-inclusive quota reservation ->
  Gemini single-chunk REST requests -> model-validated atomic vector replacement ->
  separately consented question embedding -> owner/model-scoped hybrid retrieval.
- Important files: apps/api/app/documents/gemini.py, providers.py, embeddings.py,
  indexing.py, index_worker.py, semantic.py, vectors.py; app/api/v1/routes/documents.py;
  apps/web/src/features/research/{document-indexing,passage-search}.tsx and API contracts.
- Run backend Ruff/mypy/pytest; frontend lint/typecheck/test/api:check/test:e2e.
  The PostgreSQL opt-in test requires a migrated disposable TEST_DOCUMENT_POSTGRES_URL.
  The live request checked only generic text; automated tests use fixtures.
- Debugging: a 409 disclosure_changed means refresh and review the new provider. A 429
  provider response is deferred using bounded Retry-After; the local daily budget is
  separate from Google's limits. A present key does not enable DOCUMENT_INDEXING_ENABLED.
- Test fixture settings must explicitly select their provider instead of inheriting
  the developer's .env. Private upload scanning and live reply/email work remain pending.


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

Learning notes for this increment:
- Built a reusable opt-in Gemini public-paper benchmark with request/byte caps and
  stop-on-provider-error behavior. No new package, API or migration was introduced.
- Data flow: verify frozen PDF/page hashes -> preflight budgets -> embed public chunks
  and queries outside DB transactions -> transient PostgreSQL document/vector rows ->
  production keyword/vector/hybrid retrieval -> exact-source audits -> raw JSON/metrics.
- Recall measures whether labelled evidence is found; MRR measures its rank. High
  recall on 11/17-chunk documents does not establish accuracy on a large corpus.
  Deduplication can remove distinct evidence even when chunks overlap slightly.
- Important files: apps/api/scripts/run_gemini_paper_pilot.py and
  run_public_paper_pilot.py; tests/test_gemini_pilot.py; three new Gemini result JSONs
  under apps/api/evaluation; docs/GEMINI_RETRIEVAL_PILOT.md.
- Commands: uv run ruff check .; uv run mypy app; uv run pytest; reproduce live pilots
  using the opt-in commands in the report. Offline aggregation needs no API key.
- Debugging: hash mismatches stop before sharing text. Missing key or rate limits
  stop the live run without fake-vector fallback; a network check alone is not a
  quality benchmark. Query latency excludes the deliberate two-second pacing.
- Existing LIBLINEAR font warnings persist; evidence is reviewed prose and extracted
  hashes matched. No UI/deployment change is needed for this evaluation-only work.

Final validation for the 20 October pilot: Ruff and mypy passed; full backend suite
278 passed with one opt-in PostgreSQL test skipped. Both live public-paper benchmark
runs separately exercised production FTS/vector/hybrid on migrated PostgreSQL and
completed successfully; their temporary database was removed. Seventeen focused
evaluator/source/budget tests passed. Offline recomputation exactly matched saved
combined metrics and prior keyword rankings. No frontend or deployment changes.


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

Concept: overlap is not duplication. Two sliding windows can share context while
containing different findings. Full containment guarantees the discarded source
span is already available. Data flow remains ranked candidates -> source checks
-> reciprocal-rank fusion -> containment check -> bounded cited excerpts.
Run Ruff, mypy and pytest; focused tests are tests/test_document_hybrid.py.
If a useful passage still disappears, inspect its fused rank and result limit;
this fix cannot guarantee every useful passage fits within the requested limit.
No new dependencies, migrations or frontend changes.

Validation: Ruff and mypy passed; eight focused hybrid tests passed. Full backend
suite: 283 passed, one opt-in PostgreSQL skip; the PostgreSQL integration passed
separately after starting the stopped local database. The disposable database was
removed. Offline saved-ranking replay completed without provider calls. Docker API
was rebuilt and all four local services are healthy. No frontend/API contract changes
required a frontend test rerun. Phase 2 remains active; generated answers are pending.


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

Learning notes:
- Built apps/api/app/documents/answers.py and answer_prompts.py, with regression
  tests in apps/api/tests/test_document_answers.py. Citation integrity and claim
  entailment are separate: an accurate quotation can accompany an incorrect claim.
- Flow: owner-checked ready pages + retrieved spans -> immutable evidence bundle ->
  structured candidate -> exact quote resolution -> separate context-aware review ->
  all supported claims or an explicit no-answer result. No database lock or commit
  is performed inside the provider orchestration function.
- Callers must use server-loaded evidence, commit before external I/O, enforce
  consent and quota, and recheck ownership/status before returning/persisting an
  answer. The provider protocol has no production implementation in this increment.
- Run `uv run pytest tests/test_document_answers.py` (use a project-local --basetemp
  on Windows), `uv run ruff check .`, and `uv run mypy app`. Oversized fixture values
  need short pytest IDs to avoid Windows filename/path limits.
- Debugging: invalid_provider_output means malformed JSON/references/review, not
  missing knowledge. provider_unavailable means retry may help. insufficient_evidence
  is scoped to available excerpts and does not prove the entire paper lacks an answer.
- Limits: no live model quality, prompt-injection resistance or abstention accuracy
  was measured. CV and Gmail content are outside the evidence pipeline.

Final validation: Ruff and mypy passed; full backend suite 309 passed with one
opt-in PostgreSQL skip. All 26 focused answer tests passed after the final reviewer
context change. Tests use fixture model outputs; no live generation occurred.
The new modules are not wired to an endpoint, so no app rebuild or frontend test
rerun was needed. Source and test changes were reviewed; Phase 2 remains active.


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

Concepts: transport validation rejects broken provider responses; exact-quote
validation checks provenance; semantic review estimates support but can be wrong.
Data flow: question + excerpts -> generation -> exact quote checks -> support
review -> answer or abstention. Errors return unavailable, never fabricated claims.
Run: `uv run pytest tests/test_gemini_answers.py` from apps/api. A 404 may mean
model access differs from the listing; inspect safe status codes, never log API
keys or private payloads. Main files: gemini_answers.py, answers.py,
answer_prompts.py and tests/test_gemini_answers.py. Live calls require the local
GEMINI_API_KEY. Uploads and production generation remain disabled.


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

Concepts: benchmark completeness differs from correctness; an infrastructure
failure is not an abstention. Preserving failed attempts avoids selection bias.
Data flow: verified PDFs -> frozen rankings -> top-five excerpts -> generation ->
quote validation -> support review -> incremental report. Run focused tests using
`uv run pytest tests/test_answer_pilot.py tests/test_document_answers.py tests/test_gemini_answers.py`.
Debug with safe stage codes; never print provider payloads or credentials. Existing
PDF font warnings remain, but hash verification passed. Limitations: tiny corpus,
provisional labels, incomplete runs, no independent human grading.


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

Concepts: deterministic character-to-source mapping preserves provenance; a valid
quote is distinct from a supported claim. The support reviewer can miss an uncited
qualifier. Data flow: exact match, then unique typography-only alignment, original
source slice, semantic support review. To test: uv run pytest tests/test_document_answers.py
from apps/api. Never broaden matching to silently repair words or numbers. Common
failure: model rewrites an excerpt; inspect stage codes and keep the failure visible.


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

Why: asking models to recopy PDF typography caused usable answers to be rejected.
Concept: constrained selection separates source text from generated claims.
Data flow: retrieved excerpts -> deterministic choice catalog -> selected IDs ->
exact source quotes -> claim support review -> answer/abstention/unavailable.
Run: uv run pytest tests/test_citation_choices.py tests/test_document_answers.py
from apps/api. Unknown IDs indicate invalid model output; never guess a replacement.
Limitations: selected slices may include extra context or cut sentence boundaries;
semantic review remains fallible. Unseen-paper evaluation and production consent,
quotas and owner rechecks remain necessary before release.

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

Concepts: evidence isolation reduces one source of mistaken support, while an
independent context veto preserves contradiction checking. Prompt rules are not
hard guarantees. Data flow: generation -> source resolution -> quote-only support
review -> context veto -> answer. Run: uv run pytest tests/test_document_answers.py.
Debug: a valid structured response can still contain an incorrect judgment; inspect
labelled regression outcomes, not only HTTP success. No dependencies or migrations
were introduced; UI and production endpoints remain unchanged.

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

Concepts: pessimistic owner locking serializes concurrent quota decisions in
PostgreSQL; durable reservations survive crashes; unique owner/request keys prevent
repeating a consumed request. Data flow: validated consent -> ownership/ready check
-> owner lock -> quota check -> insert/commit -> future provider call -> future
owner recheck. Run uv run pytest tests/test_answer_usage.py from apps/api. A 409
means reused request ID, 429 daily allowance exhausted, and 404 wrong/missing owner
or document. No new dependency; migration is required before future integration.

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

Concepts: transactional boundaries separate durable decisions from slow network
operations; rechecking permissions prevents returning data after access is removed.
Data flow: owner check -> retrieval -> evidence validation -> reserve/commit ->
provider calls -> owner/source recheck -> result. Run uv run pytest
tests/test_answer_service.py from apps/api. A provider failure does not refund the
allowance because the provider may already have performed work. Debug 503 by
checking the enable flag and PostgreSQL requirement, not by weakening ownership.


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

Concepts: independent database sessions exercise actual row-lock contention; a
single shared transaction cannot prove concurrency safety. Owner row locks make
the quota check and reservation insert one serialized decision. A migration round
trip checks that the new table can be removed and recreated in disposable storage.
Data flow: seed isolated owner/document -> race two transactions -> assert one
reservation -> clean fixture rows -> drop disposable database. Common error:
missing Docker Linux engine pipe means Docker Desktop is stopped; previously this
prevented the PostgreSQL checks, now resolved. Limits: a two-request race is a
regression test, not a load benchmark; no provider calls occur in these tests.

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

Concepts: transport contracts are separate from service business logic; strict
consent must not accidentally reject normal JSON UUID strings. Feature flags,
credentials and database requirements are independent gates. Data flow: authenticated
request -> document access -> gate -> provider/service -> close provider -> private
response. Run uv run pytest tests/test_answer_api.py from apps/api; export schema
with uv run python -m scripts.export_openapi, then npm run api:generate in apps/web.
503 is expected while disabled; do not set the enable flag merely to bypass it.

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

Concepts and data flow: TanStack Query loads owner-scoped availability; React Hook
Form and Zod validate input; explicit consent gates the mutation; the backend
retrieves evidence and checks claims; the UI renders quotes and selects source pages.
A ref locks submission immediately, before React renders the pending state, so rapid
clicks cannot start two requests. Backend request IDs provide another protection layer.
Files: apps/web/src/features/research/paper-answers.tsx and its tests,
paper-documents.tsx and its tests, src/lib/api/documents.ts, and
e2e/account-journey.spec.ts. Run npm run lint, npm run typecheck, npm run test,
and npm run test:e2e from apps/web. The browser runner performs a production build.
Debugging: disabled status is expected until server prerequisites are configured;
quota errors do not trigger retries. Keep UTF-8 test files to avoid mismatched
ellipsis characters in accessible labels. Existing Next.js lockfile/standalone
warnings remain. Limitations: model support checks remain fallible; answers are
not saved as a reading conversation, and citation navigation uses extracted pages.


### Connected original-PDF reader (2026-10-22)
Built an optional split reading layout so students can inspect original formatting
while checking extracted evidence and asking questions. CSS grid uses two columns
on wide screens and stacks on mobile. The selected extracted page is passed into
OriginalPdf; its object URL receives a #page fragment. React Query retains the
private Blob, so page changes do not fetch the PDF again. Effect cleanup revokes
old object URLs. PDF failures do not remove questions or extracted text.
Files: apps/web/src/features/research/paper-documents.tsx, original-pdf.tsx,
original-pdf.test.tsx and apps/web/e2e/account-journey.spec.ts.
Run npm run lint, npm run typecheck, npm run test and npm run test:e2e in apps/web.
The browser runner builds production assets before testing. Debugging: browsers
may ignore PDF fragments or refuse embedded PDFs; use extracted text, native page
controls, or the existing download fallback. No dependency added. Generation stays
disabled, and the user Docker app has not been rebuilt. Next: owner-scoped reading
conversation persistence and unseen-paper citation-support evaluation.

Validation: frontend lint/typecheck passed; 105 unit tests passed; production build and all 16 Playwright flows passed, including split-reader failure fallback, accessibility and mobile overflow checks. PDF page fragment/reuse/cleanup checks use a Blob fixture, not a real browser PDF plugin. Existing Next.js workspace-root and standalone warnings remain. Git diff whitespace check passed.
