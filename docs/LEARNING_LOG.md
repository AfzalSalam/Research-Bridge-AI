# Learning Log

Append after every phase.

## 2026-07-31 — Phase 00: Audit and foundation planning

### What was built

No application code was built. The repository, Git state, local toolchain,
product documents, and Figma Make prototype were audited. A Phase 00 execution
plan now records the current state, approved placement-release direction,
target architecture, design recommendations, risks, validation, and rollback
strategy. After approval, `PROJECT_SPEC.md`, `ROADMAP.md`, `START_HERE.md`, and
`CODEX_PROMPTS.md` were reconciled so the placement release and post-placement
ranking research are no longer mixed together.

### Why it exists

The repository contained only planning documents and had no commits. Starting
implementation without recording that baseline would make it easy to mix stale
requirements, generated prototype code, and new architecture. The audit turns
those assumptions into reviewable decisions before code exists.

### Concepts introduced

- **Greenfield repository:** a project with no existing application code to
  migrate.
- **Source of truth:** the document or artifact that wins when instructions
  disagree. Active plans, the project specification, and engineering rules must
  agree before implementation.
- **Modular monolith:** one deployable backend organized into clear modules,
  giving good separation without early microservice overhead.
- **Provenance:** the source URL, external identifier, and verification time
  retained with a fact.
- **Deterministic versus generative work:** code retrieves, validates, scores,
  and stores facts; an LLM only performs bounded explanation or drafting from
  those facts.
- **Human-in-the-loop:** email generation pauses for mentor selection and the
  draft remains editable; the system never sends it automatically.
- **Responsive task flow:** mobile may use a sequence of focused screens even
  when desktop uses a master-detail workspace.

### Data flow

There is no runtime data flow yet. The planned flow is:

```text
student profile + topic
  -> Next.js UI
  -> typed FastAPI contract
  -> deterministic service
  -> academic API/database with provenance
  -> evidence-backed mentor result
  -> user selection
  -> bounded grounded draft
  -> user review/save/copy
```

### Important files

- `AGENTS.md`: engineering and teaching rules.
- `PROJECT_SPEC.md`: current product requirements that need placement-boundary
  reconciliation.
- `ROADMAP.md`: original implementation sequence that needs a release gate.
- `CODEX_PROMPTS.md`: original prompt pack; useful as a seed but not an
  authority when it conflicts with an approved plan.
- `docs/plans/phase-00-audit-and-foundation.md`: complete audit and proposed
  foundation plan.

### How to run and test it

Phase 00 has no application tests. Inspect the documentation baseline with:

```powershell
git status --short --branch
rg --files -uu -g '!.git/**'
git diff --check
```

### Common errors and debugging

- `git log` fails because `main` has no commits. This is expected until the
  documentation baseline is accepted and committed.
- PowerShell can block `npm.ps1`; use `npm.cmd` for project scripts on this
  machine.
- Node 26 is installed but is not the intended project runtime; use Node 24 LTS.
- Python 3.14 is the default, but Python 3.13 should be pinned for the backend.
- Docker CLI exists, but the daemon was not running during the audit and the
  current Docker user config reported an access error.

### Limitations

- No application, database, API, tests, CI, or deployment exists yet.
- The Figma Make prototype was audited as a visual reference; its Vite code was
  not imported.
- The documentation is reconciled, but it describes planned behavior rather
  than an implemented application.

### Next step

Prepare and approve `docs/plans/phase-01-foundation.md`, then implement only the
reproducible frontend/backend/database foundation and its quality gates.

---

## 2026-07-31 — Phase 01: Full-stack foundation

### What was built

A production-shaped monorepo foundation now contains a Next.js App Router
frontend, a typed FastAPI backend, a PostgreSQL/pgvector Docker Compose service,
locked JavaScript and Python dependencies, environment examples, automated
quality gates, and a working health boundary between the two applications.

The foundation page intentionally demonstrates infrastructure status rather
than pretending that mentor discovery already exists. It includes an accessible
available/unavailable state and a restrained preview of the approved warm
neutral, teal, and indigo visual direction.

### Why it exists

Every later feature depends on a trustworthy application boundary. This phase
proves that the browser-facing application and API can start independently,
communicate through a versioned contract, fail safely, and be tested before any
business complexity is introduced.

### Concepts introduced

- **Monorepo:** one repository contains separately runnable frontend and backend
  applications while sharing documentation and operational configuration.
- **Server Component:** the page requests health data on the server, so browser
  JavaScript is not required for this non-interactive state.
- **Runtime validation:** TypeScript types disappear at runtime, so an unknown
  API response is checked before the UI trusts it.
- **Discriminated union:** the frontend health result is either `available` with
  typed data or `unavailable` with a safe message; each state has known fields.
- **Application factory:** FastAPI is constructed by a function, letting tests
  provide controlled settings without mutating global configuration.
- **Versioned API:** `/api/v1/health` gives future contracts a stable namespace.
- **CORS:** the API explicitly permits the development frontend origin instead
  of allowing every website to make browser requests.
- **Lockfile:** `package-lock.json` and `uv.lock` record exact resolved versions
  so installations are reproducible.
- **Dependency risk evaluation:** narrow Next.js overrides keep vulnerable
  PostCSS and Sharp versions out of production. A development-only glob advisory
  cannot currently be patched without breaking either legacy Minimatch or the
  Next.js React lint plugin, so its controlled exposure and upgrade condition
  are documented instead of hiding a broken forced resolution.
- **Install-script allowlist:** npm may execute native package setup code only
  for the inspected, pinned resolver dependency.

### Data flow

```text
GET Next.js page
  -> server-side health client
  -> GET FastAPI /api/v1/health
  -> Pydantic HealthResponse
  -> runtime payload validation
  -> accessible available/unavailable card
```

PostgreSQL is configured but is not on this request path. The health endpoint
therefore remains useful even when the database is unavailable.

### Important files

- `package.json` and `package-lock.json`: npm workspace, root commands, runtime
  policy, security overrides, and exact dependency graph.
- `apps/web/src/app/page.tsx`: dynamic Server Component and foundation page.
- `apps/web/src/lib/api/health.ts`: typed, runtime-validated API boundary.
- `apps/web/src/components/health-card.tsx`: accessible health presentation.
- `apps/api/app/main.py`: FastAPI application factory and CORS setup.
- `apps/api/app/api/v1/routes/health.py`: versioned health transport.
- `apps/api/app/core/config.py`: typed environment settings.
- `compose.yaml`: pinned local PostgreSQL 17 and pgvector service.
- `README.md`: Windows-oriented setup, run, validation, and troubleshooting.
- `docs/plans/phase-01-foundation.md`: scope, decisions, evidence, and results.

### How to run and test it

Follow `README.md` for first-time setup. The complete gates are:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build

Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
Set-Location ../..

docker compose --env-file .env.example config --quiet
```

Run the API and web development servers in separate terminals, then open
`http://localhost:3000`. A healthy local API appears as “API available.”

### Common errors and debugging

- An engine warning means the active Node runtime is not version 24. Switch to
  the `.nvmrc` version before installing dependencies.
- TypeScript 7 is not used because the current Next.js build toolchain rejects
  its changed compiler API; the project is pinned to the supported TypeScript 6
  line.
- On this Windows machine, use `npm.cmd` if PowerShell blocks `npm.ps1`.
- If npm appears to hang while using a restricted global cache, the repository
  uses an ignored project-local `.npm-cache` for repeatable commands.
- If the UI reports the API as unavailable, check that Uvicorn is listening on
  port 8000 and that `API_BASE_URL` is correct.
- A Docker named-pipe connection error means Docker Desktop is not running; it
  does not mean the Compose file is invalid.
- CORS tests use Starlette's current `httpx2` transport. Installing an unrelated
  legacy HTTPX version can reintroduce test-client warnings or incompatibility.
- A complete npm audit currently reports a Brace Expansion advisory through the
  ESLint development toolchain. Do not feed untrusted patterns into lint; track
  support for ESLint 10 in the Next.js React plugin before upgrading.

### Limitations

- The local machine had Node 26, so the pinned Node 24 target has not yet been
  exercised by CI.
- Compose configuration validates, but the PostgreSQL container was not started
  because Docker Desktop was unavailable.
- The production npm graph audits clean, but the development lint graph retains
  the documented Brace Expansion advisory until its upstream toolchain is
  compatible with the patched major release.
- Health contract types are maintained manually on both sides. Generated API
  types belong to the later contract phase.
- There are no product routes, persisted records, academic API calls, ranking,
  LLM behavior, authentication, or deployment yet.
- The visual layer is only a foundation preview; the reusable token system and
  responsive application shell belong to Phase 2.

### Next step

Create and approve `docs/plans/phase-02-design-system-and-responsive-shell.md`.
Then translate the Figma reference into design tokens and reusable primitives,
build the responsive navigation shell, and verify accessibility and reduced
motion without adding product behavior early.

---

## YYYY-MM-DD — Phase name

### What was built

### Why it exists

### Concepts introduced

### Data flow

### Important files

### How to run and test it

### Common errors and debugging

### Limitations

### Next step
