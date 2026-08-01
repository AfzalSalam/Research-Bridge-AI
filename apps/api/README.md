# Research Bridge API

Typed FastAPI modular monolith for Research Bridge AI. Start PostgreSQL from the
repository root, then run uv commands in this directory so uv discovers
`.python-version`, `pyproject.toml`, and `.env`.

```powershell
docker compose up -d db
Set-Location apps/api
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

## Current routes

- `GET /api/v1/health`: typed process health;
- `POST /api/v1/discovery/papers`: real OpenAlex paper retrieval by text, DOI,
  or OpenAlex Work ID with normalized evidence and provenance;
- `GET /api/v1/demo/bootstrap`: fictional catalog and canonical profile;
- `POST /api/v1/demo/discovery`: deterministic complete/partial/empty/error
  scenarios;
- `POST /api/v1/demo/outreach-drafts`: deterministic, evidence-bounded editable
  draft creation;
- `GET /api/v1/demo/profile`: canonical or database-saved fictional profile;
- `PUT /api/v1/demo/profile`: validate and transactionally save that profile.

Profile routes use `route -> service -> repository -> database`; the other demo
behavior remains deterministic and visibly fictional. The browser never sends
an owner ID: a server-only demo UUID partitions these rows without claiming
authentication. Every response has an `X-Request-ID`; errors share one
structured envelope. OpenAPI is available at `/docs` and checked into
`openapi.json`.

Live discovery follows `route -> service -> repository/provider -> database/API`.
The service classifies the query, checks a bounded process-local cache, asks the
typed OpenAlex provider for raw records, normalizes and deduplicates them, and
persists papers, ordered authorships, paper-specific affiliations, topics, and
provenance in one transaction. Valid records survive malformed siblings as a
`partial` response; total provider failures use safe structured errors.

`OPENALEX_API_KEY` is optional but recommended for development because the
anonymous allowance is very small. Keep it only in `apps/api/.env`; it is held
as a `SecretStr` and must never be copied to browser configuration. The API uses
the official `https://api.openalex.org` origin. A loopback HTTP origin is
accepted only in `test` or `e2e`, which lets deterministic tests use their owned
fixture server without enabling arbitrary upstream URLs in development.

## Database changes

Application startup never creates or changes tables. After pulling a schema
change, run:

```powershell
uv run alembic upgrade head
uv run alembic current --check-heads
uv run alembic check
```

Phase 6 adds `20260801_0002`, including the OpenAlex catalog fields and the
paper-author-institution relationship needed to preserve historical
affiliations. Migrations are reversible on disposable data; downgrading to base
removes all application tables.

## Contract and quality checks

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run python -m scripts.export_openapi --check
```

After an intentional Pydantic or route change, export the reviewed contract:

```powershell
uv run python -m scripts.export_openapi
```

Then run `npm.cmd run api:generate` in `apps/web` and review the generated diff.
