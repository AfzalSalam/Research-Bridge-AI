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
- `POST /api/v1/discovery/mentors`: derive paper-backed researcher candidates
  with a versioned deterministic evidence policy and explicit unknowns;
- `POST /api/v1/outreach/drafts`: verify one researcher and one or two papers,
  then create a grounded, persisted draft;
- `GET /api/v1/outreach/drafts/{draft_id}`: load the owner-scoped latest draft
  and revision summaries;
- `PUT /api/v1/outreach/drafts/{draft_id}`: save an editable revision with an
  optimistic version check;
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

Mentor discovery composes the existing profile and paper-discovery protocols,
then calls a pure relevance module. It groups repeated author IDs, retains each
paper-specific affiliation, calculates five bounded feature contributions, and
uses deterministic tie-breaking. The internal total controls review order and
evidence bands but is not returned as a misleading public fit score. Academic
title, current institution, contact, and availability remain unknown.

Live outreach reruns mentor discovery and accepts only server-resolved IDs. It
builds a typed evidence package, optionally asks the OpenAI Responses API for a
strict structured composition, audits references and unsupported language, and
falls back to `outreach-template.v1` on every unavailable, refused, invalid, or
unsafe model path. Latest draft state and immutable revision snapshots are
durable. No route sends email or discovers contact addresses.

`OPENALEX_API_KEY` is optional but recommended for development because the
anonymous allowance is very small. Keep it only in `apps/api/.env`; it is held
as a `SecretStr` and must never be copied to browser configuration. The API uses
the official `https://api.openalex.org` origin. A loopback HTTP origin is
accepted only in `test` or `e2e`, which lets deterministic tests use their owned
fixture server without enabling arbitrary upstream URLs in development.

`OPENAI_API_KEY` is also optional and server-only. Without it, outreach remains
fully usable through the deterministic fallback. `OPENAI_OUTREACH_MODEL`
defaults to `gpt-5.6-terra`; provider calls use low reasoning, strict JSON
Schema output, `store: false`, bounded output, explicit timeouts, and bounded
retries. The base URL is restricted to the official OpenAI HTTPS origin outside
tests.

## Database changes

Application startup never creates or changes tables. After pulling a schema
change, run:

```powershell
uv run alembic upgrade head
uv run alembic current --check-heads
uv run alembic check
```

Phase 8 adds `20260801_0003`, extending the latest outreach snapshot with claim
evidence and fallback metadata and adding immutable
`outreach_draft_revisions`. Migrations are reversible on disposable data;
downgrading to base removes all application tables.

## Contract and quality checks

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run python -m scripts.export_openapi --check
uv run python -m scripts.evaluate_mentor_relevance --check
uv run python -m scripts.evaluate_outreach_grounding --check
```

After an intentional Pydantic or route change, export the reviewed contract:

```powershell
uv run python -m scripts.export_openapi
```

Then run `npm.cmd run api:generate` in `apps/web` and review the generated diff.
