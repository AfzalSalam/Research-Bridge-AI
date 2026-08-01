# Research Bridge AI

Research Bridge AI is an evidence-first academic discovery and research-
opportunity platform. The repository currently contains a reproducible
full-stack foundation and the completed Phase 5 persistence boundary: a
responsive Next.js journey, a modular FastAPI backend, generated TypeScript API
types, SQLAlchemy repositories, Alembic migrations, and local PostgreSQL with
pgvector available for later phases.

The browser demo includes an editable fictional profile, transparent search
states, paper-backed fictional researcher records, deterministic custom
outreach, fictional opportunities, and an application tracker. Its profile is
durable through PostgreSQL; catalog, discovery, and draft behavior still use
explicit deterministic fixtures. No academic API, LLM, email provider, or
authentication is connected yet.

## Architecture

```text
Browser
  -> Next.js App Router (apps/web, port 3000)
      -> responsive root shell + project-owned design system
      -> TanStack Query server-state boundary
          -> same-origin /backend rewrite
              -> FastAPI /api/v1/demo
                  -> route -> service -> repository -> SQLAlchemy/PostgreSQL
                      -> durable fictional student profile
                  -> DemoService protocol -> MockDemoService
                      -> typed fictional catalog + deterministic draft
      -> validated reducer state (tab-scoped sessionStorage)
          -> selections, saved drafts, and tracker transitions
      -> typed server-side health client
          -> FastAPI (apps/api, port 8000)
              -> /api/v1/health

Docker Compose
  -> PostgreSQL 17 + pgvector (port 5432)
      -> Alembic-owned 18-table initial schema
```

FastAPI and PostgreSQL are required for the product routes. Health remains
available independently so process and database failures stay distinguishable.

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

Set-Location apps/api
uv run alembic upgrade head
Set-Location ../..
```

Alembic creates the application schema; application startup never mutates it.
The image includes pgvector, but vector columns and queries remain deferred.

### 2. Backend

Open another PowerShell window:

```powershell
Set-Location apps/api
uv run uvicorn app.main:app --reload --port 8000
```

Useful URLs:

- Health: <http://localhost:8000/api/v1/health>
- OpenAPI UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Demo bootstrap: <http://localhost:8000/api/v1/demo/bootstrap>
- Durable demo profile: <http://localhost:8000/api/v1/demo/profile>

### 3. Frontend

Open another PowerShell window at the repository root:

```powershell
npm.cmd run dev
```

Open <http://localhost:3000> and choose **Launch the product demo**. Keep FastAPI
running because the product catalog and mock operations now use its typed
contracts, and keep PostgreSQL running because bootstrap reads the durable demo
profile.

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
`example.org` evidence URLs. Profile saves survive reloads through the database;
drafts, saved opportunities, and tracker edits remain in the current browser
tab. Use **Reset demo** to clear local workflow state while retaining the last
database-saved profile.

## Quality checks

Frontend, from the repository root:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd --workspace @research-bridge/web run api:check
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd audit --omit=dev --audit-level=high
```

`test:e2e` creates a temporary migrated SQLite database, builds Next.js for an
isolated API port, owns both test servers, verifies profile persistence plus the
recruiter journey, failure, mobile, and responsive states, then removes only its
temporary data.

Backend:

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run python -m scripts.export_openapi --check
```

Compose configuration does not require the daemon:

```powershell
docker compose --env-file .env.example config
```

## Environment variables

| Variable | Application | Purpose |
| --- | --- | --- |
| `API_BASE_URL` | Next.js server | FastAPI origin used by health requests and the same-origin `/backend` rewrite. |
| `APP_NAME` | FastAPI | Human-readable service name. |
| `APP_VERSION` | FastAPI | Version returned by the health contract. |
| `APP_ENVIRONMENT` | FastAPI | Environment label such as `development`. |
| `BACKEND_CORS_ORIGINS` | FastAPI | Comma-separated browser origins allowed during local development. |
| `LOG_LEVEL` | FastAPI | Standard structured-log level such as `INFO`. |
| `DATABASE_URL` | FastAPI/Alembic | Async SQLAlchemy URL; local PostgreSQL uses the `postgresql+asyncpg` dialect. |
| `DATABASE_ECHO` | FastAPI | Opt-in SQL logging for local debugging; keep disabled around private data. |
| `DEMO_OWNER_ID` | FastAPI | Server-only UUID ownership anchor for the fictional profile. |
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
Product routes show an explicit retryable error if FastAPI is absent.

### Profile saves fail while health still works

Start PostgreSQL and apply migrations with `uv run alembic upgrade head`. The
health route checks the API process; product routes intentionally fail safely if
their database is unavailable or behind the current migration head.

### Port 5432 reaches a different PostgreSQL service

Set `POSTGRES_PORT=55432` before `docker compose up -d db` and update the port in
`DATABASE_URL`. This machine had another PostgreSQL listener on 5432, so the
live Phase 5 smoke test deliberately used 55432.

### Some demo changes disappeared

Only the fictional profile is durable in Phase 5. Drafts, saves, and tracker
changes use `sessionStorage`, so they are scoped to the current browser tab.

### uv selects Python 3.14

Run uv inside `apps/api`. Its `.python-version` and `requires-python` constraint
select Python 3.13. You can verify it with:

```powershell
uv run python --version
```

### Docker cannot connect to the engine

Start Docker Desktop and wait until its engine reports ready. `docker compose
config` can still validate the YAML without starting a container.

### A complete npm audit reports a generator advisory

The deployable production graph audits clean. The pinned OpenAPI generator has
one moderate development-only template advisory; it processes only the
repository-owned `apps/api/openapi.json`. Newer generator versions remove that
advisory but currently pull a high-severity YAML parser advisory. The pin and
upgrade condition are recorded in the Phase 4 plan instead of hiding the
tradeoff with a forced install.

## Documentation

- Engineering rules: `AGENTS.md`
- Product specification: `PROJECT_SPEC.md`
- Roadmap: `ROADMAP.md`
- Phase 1 plan: `docs/plans/phase-01-foundation.md`
- Phase 2 plan: `docs/plans/phase-02-design-system-and-responsive-shell.md`
- Phase 3 plan: `docs/plans/phase-03-typed-mock-product-journey.md`
- Phase 4 plan: `docs/plans/phase-04-backend-contracts.md`
- Phase 5 plan: `docs/plans/phase-05-database-and-profile.md`
- Learning log: `docs/LEARNING_LOG.md`
