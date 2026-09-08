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
Phase 14 — Post-placement ranking and enrichment research (evaluating pgvector, embeddings, and cross-encoder reranking).
