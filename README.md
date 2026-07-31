# Research Bridge AI

Research Bridge AI is an evidence-first academic discovery and research-
opportunity platform. The current repository phase contains the reproducible
full-stack foundation: a Next.js frontend, a FastAPI backend, and local
PostgreSQL with pgvector available for later phases.

Product features such as profiles, OpenAlex search, mentor relevance, outreach
drafting, internships, and authentication are intentionally not implemented in
Phase 1. See `PROJECT_SPEC.md`, `ROADMAP.md`, and the active plan under
`docs/plans/` for the approved sequence.

## Architecture

```text
Browser
  -> Next.js App Router (apps/web, port 3000)
      -> typed server-side health client
          -> FastAPI (apps/api, port 8000)
              -> /api/v1/health

Docker Compose
  -> PostgreSQL 17 + pgvector (port 5432)
```

The health endpoint deliberately does not depend on PostgreSQL. It confirms
that the API process and typed frontend/backend boundary work even while the
database is unavailable.

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

Open <http://localhost:3000>. The page shows either the typed API health
response or an honest unavailable state.

## Quality checks

Frontend, from the repository root:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd audit --omit=dev --audit-level=high
```

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
- Learning log: `docs/LEARNING_LOG.md`
