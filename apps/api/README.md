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

## Database changes

Application startup never creates or changes tables. After pulling a schema
change, run:

```powershell
uv run alembic upgrade head
uv run alembic current --check-heads
uv run alembic check
```

The initial migration is reversible with `uv run alembic downgrade base`, but
that removes all application tables and should only be used on disposable data.

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
