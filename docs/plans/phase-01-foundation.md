# Phase 01 — Full-Stack Foundation

**Status:** Complete

**Prepared:** 2026-07-31

**Scope:** Reproducible frontend, backend, database container, health contract,
quality gates, and developer documentation only

## 1. Outcome

Create the smallest production-shaped Research Bridge AI monorepo that proves
the frontend, backend, and local database can be developed and validated
independently.

At the end of this phase:

- a Next.js App Router page displays the state of a typed FastAPI health API;
- the FastAPI application exposes `GET /api/v1/health`;
- PostgreSQL with pgvector can be started through Docker Compose;
- runtime versions and dependencies are pinned or locked;
- frontend and backend lint, type-check, test, and build gates pass;
- a new contributor can run the foundation from Windows using the README.

This phase proves the system boundary. It does not implement the product
journeys described in the specification.

## 2. Starting state

- Phase 00 is approved and complete.
- The original documentation is preserved in Git commit `60e9b5f`.
- The placement-release documentation is reconciled in commit `93beace`.
- No application code, package manifest, lockfile, environment file, database,
  test suite, or CI configuration exists.
- Node.js 26 is installed locally, but Node 24 is the current Active LTS line
  and will be the project target.
- Python 3.13 is installed and will be selected explicitly because Python 3.14
  is the machine default.
- Docker CLI is installed, but Docker Desktop/daemon was not running during
  Phase 00.

## 3. Architecture boundary

```text
Next.js Server Component
  -> typed health client
      -> HTTP GET /api/v1/health
          -> FastAPI versioned router
              -> typed HealthResponse

Docker Compose
  -> PostgreSQL 17 + pgvector extension image
```

The frontend and backend remain separate applications. Next.js is not used as
a substitute backend. The database exists only as infrastructure in this phase;
the health route does not require it and no business tables are created.

## 4. Repository structure

```text
/
  .editorconfig
  .gitattributes
  .gitignore
  .nvmrc
  .env.example
  README.md
  compose.yaml
  package.json
  package-lock.json
  apps/
    web/
      .env.example
      package.json
      next.config.ts
      tsconfig.json
      eslint.config.mjs
      postcss.config.mjs
      vitest.config.mts
      src/
        app/
        components/
        lib/api/
        test/
    api/
      .env.example
      .python-version
      pyproject.toml
      uv.lock
      app/
        api/v1/routes/
        core/
        schemas/
      tests/
  docs/
    plans/phase-01-foundation.md
    LEARNING_LOG.md
```

Generated caches, build outputs, virtual environments, real `.env` files, and
database volumes must remain ignored.

## 5. Implementation decisions

### JavaScript workspace

- Use an npm workspace at the repository root with `apps/web` as the first
  package.
- Pin Node major version 24 in `.nvmrc` and the package `engines` field.
- Commit the root `package-lock.json` so local and CI installs resolve the same
  dependency graph.
- Use `npm.cmd` in Windows documentation because this machine’s PowerShell
  execution policy can block `npm.ps1`.

### Frontend

- Use the current Next.js App Router with strict TypeScript, Tailwind CSS, and
  ESLint core-web-vitals/TypeScript rules.
- Keep the landing page a Server Component. It calls a small typed health
  client and renders a synchronous presentational health component.
- Mark the page dynamic so a production build does not require the backend to
  be running.
- Validate the unknown JSON health payload before treating it as typed data.
- Return a safe unavailable state rather than exposing a raw network error.
- Use Vitest, jsdom, React Testing Library, and jest-dom for focused unit and
  component tests. Async Server Components remain outside the unit-test target;
  the synchronous component and API client are tested separately.
- Add only a minimal foundation presentation. Figma token translation,
  shadcn/ui, responsive navigation, and the full visual system belong to Phase
  2.

### Backend

- Pin Python to the 3.13 minor line using `.python-version` and
  `requires-python`.
- Use uv with a committed cross-platform `uv.lock`.
- Use FastAPI, Pydantic Settings, and Uvicorn as runtime dependencies.
- Use Starlette’s current `httpx2` test transport, plus pytest, Ruff, and mypy
  as development dependencies. The selected HTTPX external client is added when
  real academic API calls begin.
- Keep settings in one typed object. Local CORS origins come from configuration
  and are explicit rather than wildcarded.
- Expose a typed `HealthResponse` from a versioned router.
- Use an application factory so tests can construct an isolated application
  with explicit settings.
- Do not create a fake service or repository layer for a constant health
  response. The route contains transport/system-status logic only.

### Database container

- Pin `pgvector/pgvector:0.8.2-pg17-bookworm` rather than a floating tag.
- Configure a named volume, local-only credentials from environment/defaults,
  and a PostgreSQL health check.
- Make pgvector available for future phases without creating vectors, tables,
  or ranking logic now.

### Environment variables

- Commit examples only; never commit a real `.env`.
- `API_BASE_URL` is server-only in Next.js. Do not put secrets in
  `NEXT_PUBLIC_*`.
- Backend CORS configuration explicitly permits the local frontend origin.
- Compose credentials are development defaults and are not production secrets.

## 6. Dependencies and why they exist

| Dependency | Scope | Reason |
| --- | --- | --- |
| `next`, `react`, `react-dom` | Frontend runtime | Required Next.js App Router runtime. |
| `tailwindcss`, `@tailwindcss/postcss` | Frontend build | Required approved styling stack; only basic setup in this phase. |
| `typescript`, `@types/*` | Frontend development | Strict static type checking. |
| `eslint`, `eslint-config-next` | Frontend development | Next.js, React, accessibility-adjacent, and Core Web Vitals lint rules. |
| `vitest`, `jsdom` | Frontend tests | Fast unit/component test runner and browser-like DOM. |
| `@testing-library/react`, `@testing-library/dom`, `@testing-library/jest-dom` | Frontend tests | User-facing component queries and accessible assertions. |
| `@vitejs/plugin-react` | Frontend tests | JSX transformation in Vitest; Vite's native `resolve.tsconfigPaths` handles aliases. |
| `fastapi` | Backend runtime | Typed ASGI API framework selected by the architecture. |
| `pydantic-settings` | Backend runtime | Typed environment configuration without handwritten parsing. |
| `uvicorn[standard]` | Backend runtime | Local ASGI server. |
| `httpx2` | Backend tests | Current HTTP transport used by Starlette/FastAPI’s synchronous test client. |
| `pytest` | Backend tests | Python test runner. |
| `ruff` | Backend development | Fast linting and formatting checks. |
| `mypy` | Backend development | Static Python type checking. |

No query library, form library, shadcn component, database ORM, migration tool,
academic client, LLM SDK, LangGraph package, authentication SDK, or deployment
SDK is added in this phase because none is needed for the health boundary.

## 7. Milestones

### A. Repository foundation

- [x] Add line-ending, editor, ignore, and runtime-version files.
- [x] Add root npm workspace and commands.
- [x] Add environment examples and Docker Compose.
- [x] Add Windows-friendly README.

### B. Backend foundation

- [x] Create uv project pinned to Python 3.13.
- [x] Add typed settings and application factory.
- [x] Add versioned health route and response schema.
- [x] Add explicit local CORS.
- [x] Add health and CORS tests.
- [x] Configure Ruff, mypy, and pytest.

### C. Frontend foundation

- [x] Create Next.js App Router package with strict TypeScript.
- [x] Add typed runtime-validated health client.
- [x] Add accessible health display and safe unavailable state.
- [x] Add frontend client/component tests.
- [x] Configure lint, type-check, test, and build commands.

### D. Validation and teaching

- [x] Generate and inspect both dependency lockfiles.
- [x] Run every frontend quality gate.
- [x] Run every backend quality gate.
- [x] Validate Compose configuration.
- [x] Run a local frontend/backend smoke check when possible.
- [x] Update this checklist with actual results.
- [x] Append the Phase 1 learning-log entry.
- [x] Review the full Git diff and secret scan.

## 8. Validation results

- Frontend lint, strict type-check, four Vitest tests, and the production build
  pass.
- Backend Ruff lint and formatting, strict mypy, and two pytest tests pass.
- `docker compose --env-file .env.example config --quiet` passes.
- The live Next.js-to-FastAPI smoke check passes, including the typed `ok`
  health state, semantic page structure, keyboard focus, and mobile overflow
  check at 390 pixels.
- The database container could not be started because Docker Desktop was not
  running. No database behavior is part of this phase.
- The deployable production npm graph reports zero known vulnerabilities.
  Narrow Next.js overrides select patched PostCSS and Sharp releases, and the
  only allowed install script belongs to the pinned native resolver package.
  The development graph retains a high-severity Brace Expansion advisory in the
  current Next.js ESLint toolchain. Both available forced resolutions were
  rejected after verification: overriding the transitive package breaks legacy
  Minimatch, while ESLint 10 breaks the current React lint plugin. The exposed
  input is repository-controlled lint globs, not application or user input.
- Validation ran on the machine's Node 26 installation. Repository metadata
  deliberately targets Node 24 LTS; CI validation on that exact runtime remains
  a Phase 12 task.

## 9. Validation commands

Run from the repository root unless a directory is shown.

```powershell
npm.cmd install
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build

Set-Location apps/api
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
Set-Location ../..

docker compose --env-file .env.example config
```

If Docker Desktop is available:

```powershell
docker compose --env-file .env.example up -d db
docker compose ps
docker compose down
```

The database container may be reported as an environmental limitation when the
daemon is unavailable, but Compose configuration must still validate.

## 10. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Local Node 26 masks Node 24 incompatibility | Pin Node 24 in files and CI-ready engines; keep code within documented Next.js requirements. |
| ESLint's development-only glob dependency has an open advisory | Keep the production graph clean, avoid untrusted lint patterns, and upgrade after the Next.js React lint plugin supports ESLint 10. |
| Package-manager network or cache is restricted | Retry only the required install with approved network access; commit lockfiles. |
| The frontend build calls an unavailable backend | Use a dynamic Server Component and a safe unavailable state. |
| CORS is made permissive for convenience | Use explicit configured origins and test the allowed local origin. |
| Health code grows into premature architecture | Keep a small versioned route/schema and defer business layers to Phase 4. |
| Docker daemon remains unavailable | Validate Compose statically and report the runtime smoke test honestly. |
| Generated UI drifts into Phase 2 | Keep this page intentionally minimal and do not import Figma Make code. |
| Secrets enter the repository | Commit examples only and run a final secret-oriented scan. |

## 11. Rollback strategy

- Phase 1 adds new foundation files and should not modify unrelated user work.
- Review the exact diff before staging.
- Record the accepted implementation in one clear Phase 1 commit.
- Roll back later with `git revert` of that commit; do not use destructive reset
  commands.
- Local caches, `.venv`, `.next`, and `node_modules` are disposable ignored
  outputs and are not part of rollback.
- The named database volume contains no business data in this phase. Do not
  remove it automatically; document any explicit cleanup command separately.

## 12. Out of scope

- Figma token implementation and shadcn/ui components.
- Product routes and mock mentor/internship flows.
- Business API contracts.
- SQLAlchemy, Alembic, or business tables.
- OpenAlex or any external academic request.
- Relevance, ranking, embeddings, or pgvector queries.
- LLMs, email drafting, or LangGraph.
- Authentication, resume upload, scraping, cloud services, or deployment.

## 13. Completion rule

Phase 1 is complete only when the required files exist, all runnable quality
gates pass, environmental failures are reported honestly, the learning log is
updated, and the full diff contains no secret or future-phase implementation.

The exact next step after acceptance is **Phase 2 — Design system and responsive
shell**, beginning with a new approved execution plan and a fresh inspection of
the Figma reference.
