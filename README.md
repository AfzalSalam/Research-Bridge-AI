# Research Bridge AI

Research Bridge AI is an evidence-first academic discovery and research-
opportunity platform. The repository currently contains a reproducible
full-stack foundation and the completed Phase 3 product demo: a responsive
Next.js journey, a FastAPI backend, and local PostgreSQL with pgvector available
for later phases.

The browser demo includes an editable fictional profile, transparent fixture
search states, paper-backed fictional researcher records, deterministic custom
outreach, fictional opportunities, and an application tracker. It is visibly
mocked: no academic API, LLM, email provider, authentication, or durable
database is connected yet. See `PROJECT_SPEC.md`, `ROADMAP.md`, and the active
plan under `docs/plans/` for the approved sequence.

## Architecture

```text
Browser
  -> Next.js App Router (apps/web, port 3000)
      -> responsive root shell + project-owned design system
      -> validated DemoProvider state (tab-scoped sessionStorage)
          -> typed fictional fixtures
          -> deterministic evidence-grounded draft template
          -> profile, discovery, mentors, opportunities, applications
      -> typed server-side health client
          -> FastAPI (apps/api, port 8000)
              -> /api/v1/health

Docker Compose
  -> PostgreSQL 17 + pgvector (port 5432)
```

The Phase 3 journey is deliberately local and works without FastAPI. The
landing-page health endpoint still confirms the typed frontend/backend boundary
and deliberately does not depend on PostgreSQL.

## Prerequisites

- Node.js 24 LTS. The repository pins the major version in `.nvmrc`.
- npm 11.
- Python 3.13.
- uv.
- Docker Desktop when running PostgreSQL.

This repository was prepared on Windows PowerShell. Use `npm.cmd` if PowerShell
blocks the `npm.ps1` shim.

## First-time setup

From the repository root:

```powershell
Copy-Item .env.example .env
Copy-Item apps/web/.env.example apps/web/.env.local
Copy-Item apps/api/.env.example apps/api/.env

npm.cmd install

Set-Location apps/api
uv sync --all-groups
Set-Location ../..
```

The copied `.env` files are ignored by Git. Never place real credentials or API
keys in an example file.

## Run locally

### 1. Database

Start Docker Desktop, then from the repository root:

```powershell
docker compose --env-file .env up -d db
docker compose ps
```

The image includes pgvector, but no application schema or vector query is added
until a later phase.

### 2. Backend

Open another PowerShell window:

```powershell
Set-Location apps/api
uv run uvicorn app.main:app --reload --port 8000
```

Useful URLs:

- Health: <http://localhost:8000/api/v1/health>
- OpenAPI UI: <http://localhost:8000/docs>

### 3. Frontend

Open another PowerShell window at the repository root:

```powershell
npm.cmd run dev
```

Open <http://localhost:3000> and choose **Launch the product demo**. FastAPI and
PostgreSQL are optional for the Phase 3 fictional journey; start them when you
want the landing page to show a healthy full-stack boundary.

Useful frontend routes:

- `/design-system`: internal tokens, primitives, form patterns, and data-state
  gallery;
- `/profile`: validated fictional student context;
- `/discover`: transparent complete, partial, empty, error, and loading fixture
  scenarios;
- `/mentors`: responsive master-detail evidence and editable deterministic
  outreach;
- `/opportunities`: source-linked fictional listings, unknown fields, filters,
  and save actions;
- `/applications`: explicit status, notes, follow-up, and event history.

Every person, paper, institution, and opportunity is fictional and uses inert
`example.org` evidence URLs. Changes remain in the current browser tab. Use
**Reset demo** on any product route to restore the canonical fixture state.

## Quality checks

Frontend, from the repository root:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd audit --omit=dev --audit-level=high
```

`test:e2e` creates a production build, starts an isolated local server, runs the
desktop recruiter journey plus mobile and responsive-matrix checks, and then
stops the server.

Backend:

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

Compose configuration does not require the daemon:

```powershell
docker compose --env-file .env.example config
```

## Environment variables

| Variable | Application | Purpose |
| --- | --- | --- |
| `API_BASE_URL` | Next.js server | FastAPI origin used by the server-side health client. |
| `APP_NAME` | FastAPI | Human-readable service name. |
| `APP_VERSION` | FastAPI | Version returned by the health contract. |
| `APP_ENVIRONMENT` | FastAPI | Environment label such as `development`. |
| `BACKEND_CORS_ORIGINS` | FastAPI | Comma-separated browser origins allowed during local development. |
| `POSTGRES_*` | Docker Compose | Local database name, user, password, and host port. |

`API_BASE_URL` is intentionally server-only. Do not move secrets into a
`NEXT_PUBLIC_*` variable because those values are included in browser assets.

## Common issues

### `npm.ps1` cannot be loaded

Run `npm.cmd` instead of `npm` from PowerShell.

### The page says the API is unavailable

Start FastAPI on port 8000 and confirm `apps/web/.env.local` contains:

```text
API_BASE_URL=http://localhost:8000
```

Restart the Next.js development server after changing environment variables.
The Phase 3 demo routes still work because they are intentionally local.

### Demo changes disappeared

Phase 3 uses `sessionStorage`, so data is scoped to the current browser tab.
Closing the tab or choosing **Reset demo** returns to the canonical fictional
fixtures. Durable persistence arrives in a later database phase.

### uv selects Python 3.14

Run uv inside `apps/api`. Its `.python-version` and `requires-python` constraint
select Python 3.13. You can verify it with:

```powershell
uv run python --version
```

### Docker cannot connect to the engine

Start Docker Desktop and wait until its engine reports ready. `docker compose
config` can still validate the YAML without starting a container.

### A complete npm audit reports the lint glob advisory

The deployable production graph audits clean. The current Next.js ESLint
toolchain still uses legacy Minimatch/Brace Expansion for repository-controlled
lint patterns. Forcing the patched major breaks that API, and forcing ESLint 10
breaks the current React lint plugin. Keep lint patterns trusted and use the
documented production audit until the upstream lint stack becomes compatible;
the decision and retest evidence are recorded in the Phase 1 plan.

## Documentation

- Engineering rules: `AGENTS.md`
- Product specification: `PROJECT_SPEC.md`
- Roadmap: `ROADMAP.md`
- Phase 1 plan: `docs/plans/phase-01-foundation.md`
- Phase 2 plan: `docs/plans/phase-02-design-system-and-responsive-shell.md`
- Phase 3 plan: `docs/plans/phase-03-typed-mock-product-journey.md`
- Learning log: `docs/LEARNING_LOG.md`
