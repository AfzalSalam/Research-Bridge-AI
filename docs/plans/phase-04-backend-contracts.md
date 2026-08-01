# Phase 04 — Backend Contracts

**Status:** Complete

**Prepared:** 2026-08-01

**Scope:** A versioned, observable FastAPI mock boundary and a generated,
contract-checked TypeScript client that replace direct frontend fixture access
without changing the Phase 3 product journey

## 1. Outcome

Move the fictional recruiter demo behind a real HTTP contract while keeping its
behavior honest, deterministic, and easy to explain.

At the end of this phase:

1. FastAPI exposes modular versioned product routes;
2. routes delegate business behavior through typed service interfaces;
3. the demo implementation returns visibly fictional records;
4. validation and operational failures use one structured error envelope;
5. every response carries a traceable request ID;
6. the checked-in OpenAPI document generates the frontend transport types;
7. TanStack Query owns remote bootstrap state and request mutations;
8. frontend feature code no longer imports the fixture catalog directly;
9. the existing browser-session edits and application tracker still work; and
10. no ranking, real provider, LLM, database, authentication, or email sending
    is implied.

## 2. Starting state and preservation

- Phase 3 is committed as `c4be6ca` and implements the complete typed fictional
  journey.
- The repository owner subsequently created commit `6138f9e` (`version1`). It is
  part of the preserved baseline and will not be rewritten.
- The working tree was clean when Phase 4 planning began.
- FastAPI currently exposes only `GET /api/v1/health`.
- Frontend product routes currently read canonical records from
  `features/demo/fixtures.ts` and create outreach with a local deterministic
  template.
- Session storage intentionally remains browser-local until authenticated
  persistence is introduced in a later phase.

## 3. Product boundary

### 3.1 Remote in Phase 4

- canonical fictional student profile;
- fictional paper, mentor, and opportunity catalog;
- deterministic demo discovery outcomes;
- deterministic evidence-bounded outreach draft creation.

### 3.2 Still local in Phase 4

- edited profile state;
- selected mentor and papers;
- editable/saved draft text after creation;
- saved opportunity IDs;
- application tracker records and status history;
- session reset.

These are user-session writes and belong in PostgreSQL only after Phase 5
establishes durable models, migrations, repositories, and transaction rules.

### 3.3 Explicitly absent

- ranking or numeric match scores;
- OpenAlex or other academic-provider calls;
- professor identity resolution;
- LLM generation or LangGraph;
- login, authorization, database writes, background jobs, and email sending.

## 4. API surface

All product routes live under `/api/v1/demo`.

### `GET /bootstrap`

Returns:

- `schemaVersion`;
- canonical fictional `profile`;
- `mentors`, each containing its paper evidence;
- `opportunities`;
- explicit `mode: "fictional-demo"`.

This is one small bootstrap resource for the current demo, not a production
pagination strategy. Later phases will introduce independently paginated
resources when the catalog becomes real and larger.

### `POST /discovery`

Accepts:

- trimmed query text;
- one closed demo scenario.

Returns one of the same Phase 3 outcomes:

- `complete` with paper and mentor IDs;
- `partial` with IDs and a source warning;
- `empty` with no IDs;
- `error` through the structured error envelope.

The service does not calculate a score or pretend to retrieve providers.

### `POST /outreach-drafts`

Accepts:

- the currently edited, validated student profile;
- one mentor ID;
- one or two selected supporting paper IDs.

Returns an editable deterministic draft with:

- subject and body;
- selected student facts;
- evidence IDs and claim notes;
- uncertainty warnings;
- generation mode and template version;
- created/updated timestamps.

Unknown mentor contact or availability remains unknown. The route cannot send
or schedule an email.

## 5. Backend architecture

```text
HTTP request
  -> request-ID and timing middleware
  -> versioned route (transport and status codes)
  -> DemoService protocol (business contract)
  -> MockDemoService (deterministic behavior)
  -> fictional fixture repository in memory
  -> Pydantic response validation
  -> structured log + X-Request-ID response header
```

Planned modules:

```text
app/
  api/v1/routes/demo.py
  core/errors.py
  core/logging.py
  core/middleware.py
  dependencies/services.py
  fixtures/demo.py
  schemas/base.py
  schemas/demo.py
  schemas/errors.py
  services/demo.py
  services/mock_demo.py
scripts/export_openapi.py
openapi.json
```

Routes contain HTTP concerns only. The service owns validation that depends on
the catalog and deterministic draft/discovery behavior. The fixture module owns
data, not behavior.

## 6. Contract conventions

- Python internals use `snake_case`.
- Public JSON uses `camelCase` to preserve the approved TypeScript UI model.
- A shared Pydantic base model enables alias generation and strict extra-field
  rejection where input correctness matters.
- Closed sets use literals/enums rather than arbitrary strings.
- IDs are opaque strings in this mock phase.
- Dates and timestamps use ISO 8601 strings validated as `date`/`datetime`.
- URLs are validated and stay on reserved `example.org` domains.
- API responses are validated by FastAPI before delivery.
- OpenAPI is checked in so contract changes are reviewable in Git.

## 7. Errors and observability

Expected failures return:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request could not be validated.",
    "requestId": "...",
    "details": []
  }
}
```

Rules:

- predictable domain failures use a typed `AppError`;
- request validation maps to HTTP 422 and safe field-level details;
- unmatched routes and HTTP failures use the same envelope;
- unexpected failures are logged with a stack trace but return a generic 500
  message;
- no secrets, resume contents, profile body, or email draft body are logged;
- a valid inbound `X-Request-ID` may be continued, otherwise a UUID is created;
- the response always exposes `X-Request-ID`;
- one structured completion log records method, path, status, request ID, and
  elapsed time.

## 8. Frontend integration

### 8.1 Generated contract

`@hey-api/openapi-ts` generates `src/lib/api/generated/` from the checked-in
OpenAPI document, including a typed Fetch transport. This TypeScript 6-compatible
generator prevents hand-maintained request/response types from drifting away
from FastAPI.

Generation flow:

```text
Pydantic schemas -> FastAPI OpenAPI -> apps/api/openapi.json
  -> @hey-api/openapi-ts -> apps/web/src/lib/api/generated/
```

A check command regenerates to a temporary file and compares it with the
checked-in result so CI detects drift.

### 8.2 Server-state ownership

TanStack Query manages:

- bootstrap loading, success, failure, and retry;
- discovery mutation pending/error/success;
- outreach-draft mutation pending/error/success.

React Context + reducer continues to manage editable local workflow state. This
separation is intentional: server state is cached/fetched; user editing state
has deterministic local transitions.

### 8.3 Runtime validation

Generated types protect compilation but do not validate network bytes. The
existing Zod schemas remain the runtime trust boundary. API wrapper functions
parse successful JSON before feature code receives it and parse error envelopes
before showing safe messages and request IDs.

### 8.4 Connectivity

Browser requests use a same-origin Next.js rewrite (`/backend/*`) that targets
the server-only `API_BASE_URL`. This avoids exposing configuration as a public
environment value and avoids coupling browser code to deployment topology.

## 9. Loading and failure behavior

- The root provider renders product navigation immediately.
- Product screens show the shared loading state while bootstrap is pending.
- Bootstrap failure shows a retry action and request ID when available.
- Invalid bootstrap data is treated as a contract failure, never silently used.
- Discovery retains the four approved visible outcome states.
- Draft creation keeps existing selections and shows an inline retryable error.
- Local session data is hydrated only after a valid bootstrap catalog exists.
- Reset restores the backend-provided canonical profile and clears local edits.

## 10. Dependencies

| Dependency | Scope | Reason |
| --- | --- | --- |
| `@tanstack/react-query` | frontend runtime | Required repository server-state layer; supplies caching, request status, mutation state, and retry control. |
| `@hey-api/openapi-ts` | frontend development | TypeScript 6-compatible generator that creates reviewable types, SDK functions, and a Fetch client from FastAPI OpenAPI. |

No Python runtime dependency is required. Request IDs, timing, context, and JSON
logging use the standard library and FastAPI/Starlette facilities already
installed.

## 11. Test strategy

### Backend

- bootstrap returns valid fictional typed records;
- discovery returns complete, partial, and empty outcomes;
- simulated discovery failure returns the structured error envelope;
- outreach uses only selected student, mentor, and paper facts;
- unknown IDs and invalid paper counts fail safely;
- validation, 404, and unexpected errors share the documented shape;
- supplied/generated request IDs appear in headers, envelopes, and logs;
- service dependencies can be overridden in tests;
- OpenAPI contains every route and shared error schema.

### Frontend

- generated contract is current;
- API wrappers parse success and structured failure responses;
- provider exposes loading, error/retry, success, and session hydration;
- feature modules do not import the fixture catalog;
- discovery and draft mutations preserve approved behavior;
- reducer tests remain deterministic.

### End to end

The runner starts both FastAPI and the production Next.js server, then verifies:

1. bootstrap arrives through the mock backend;
2. the full profile-to-tracker flow still succeeds;
3. simulated partial/empty/error discovery states remain understandable;
4. no send action exists;
5. responsive, keyboard, and reduced-motion checks still pass.

## 12. Quality gates

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
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

Manual browser QA covers loading, retryable API error, success, mobile layout,
keyboard focus, browser console, and request-ID visibility.

## 13. Milestones

### A. Contract foundation

- [x] Add shared Pydantic base/error contracts.
- [x] Add request-ID, structured logging, and exception handling.
- [x] Add service protocol and dependency provider.

### B. Mock product API

- [x] Move canonical fictional data to the backend fixture adapter.
- [x] Add bootstrap, discovery, and outreach-draft service behavior.
- [x] Add modular versioned routes and API tests.

### C. Contract generation and frontend adapter

- [x] Export and check in OpenAPI.
- [x] Add generated TypeScript types and typed transport.
- [x] Add TanStack Query root provider.
- [x] Replace direct fixture and template access in feature modules.

### D. Verification and teaching

- [x] Add contract, integration, component, and E2E coverage.
- [x] Pass backend and frontend gates.
- [x] Verify responsive/accessibility/error behavior in a browser.
- [x] Update README, ROADMAP, and `docs/LEARNING_LOG.md`.
- [x] Review full diff and scan for secrets/private data.

## 14. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Generated types are mistaken for runtime validation | Keep Zod parsing at the network boundary. |
| Frontend becomes unavailable whenever API is down | Provide explicit loading/error/retry states; offline fixture fallback would hide an outage and is not used. |
| Duplicate Python and TypeScript models drift | Generate transport types from OpenAPI and enforce a drift check. |
| Mock routes look like production intelligence | Keep `/demo`, `fictional-demo`, fixture labels, reserved URLs, and not-ranked language visible. |
| Routes accumulate business logic | Test the service separately and keep routes limited to transport mapping. |
| Logging leaks user-entered profile or draft text | Log metadata only and test the structured record shape. |
| One bootstrap payload becomes a long-term API design | Document it as a bounded demo adapter and replace with pagination when live retrieval begins. |
| E2E becomes process-dependent | Use one cross-platform runner that owns or safely reuses both local servers. |
| Contract generator security fixes create a worse transitive risk | Pin `@hey-api/openapi-ts` 0.97.0, process only the trusted checked-in contract, keep production audit clean, and retest the generator dependency tree before upgrading. |

## 15. Rollback

- Phase 3 remains recoverable as commit `c4be6ca`.
- The owner's `6138f9e` commit remains untouched.
- Phase 4 is captured as one reviewable commit after all gates pass.
- The backend is stateless and all user-editable data remains resettable
  browser-session state.

## 16. Completion rule

Phase 4 is complete only when the frontend journey uses the FastAPI mock
contracts instead of direct fixture access, OpenAPI-to-TypeScript drift is
checked, structured failures and request IDs are test-covered, all quality
gates pass, documentation teaches the boundary, and no future-phase feature has
been introduced.

The exact next step after acceptance is **Phase 5 — Database and profile**:
introduce PostgreSQL models, repositories, Alembic migrations, and durable
storage for the approved product entities.

## 17. Verification evidence

- Backend: Ruff check and format check, mypy, OpenAPI drift check, and 11 pytest
  tests pass.
- Frontend: generated-contract drift check, ESLint, strict TypeScript, 17
  Vitest tests, and the production build pass.
- Full journey: five Playwright tests pass against FastAPI and production
  Next.js, including complete, partial, empty, structured-error, keyboard,
  reduced-motion, and 360/390/768/1280 responsive paths.
- Manual browser QA: desktop discovery and 390px mentor views are readable,
  the page has no horizontal overflow, the simulated error exposes its request
  reference, and expected handled failures leave no console warning/error.
- Security/configuration: production npm audit reports zero known
  vulnerabilities, the full development audit has one documented moderate
  generator advisory, and Docker Compose configuration validates.
- Environment notes: Node 26 prints an engine warning because the repository
  supports Node 24; a temporary `UV_CACHE_DIR` is used only when the restricted
  shell cannot write to uv's global cache.
