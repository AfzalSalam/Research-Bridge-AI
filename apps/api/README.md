# Research Bridge API

Typed FastAPI modular monolith for Research Bridge AI. Run commands in this
directory so uv discovers `.python-version`, `pyproject.toml`, and `.env`.

```powershell
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
```

## Current routes

- `GET /api/v1/health`: typed process health;
- `GET /api/v1/demo/bootstrap`: fictional catalog and canonical profile;
- `POST /api/v1/demo/discovery`: deterministic complete/partial/empty/error
  scenarios;
- `POST /api/v1/demo/outreach-drafts`: deterministic, evidence-bounded editable
  draft creation.

All product routes remain stateless and visibly fictional. Every response has
an `X-Request-ID`; errors share one structured envelope. OpenAPI is available at
`/docs` and checked into `openapi.json`.

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
