# Phase 05 — Database and profile

**Status:** Complete

**Prepared:** 2026-08-01

**Completed:** 2026-08-01

**Scope:** Establish the PostgreSQL persistence model, migration discipline,
ownership-ready records, transaction/repository boundary, and durable demo
profile integration without introducing authentication or future retrieval,
ranking, opportunity-ingestion, or LLM behavior.

## 1. Outcome

At the end of this phase:

1. SQLAlchemy 2 models describe the approved placement-release entities;
2. Alembic owns every database schema change from an initial migration;
3. PostgreSQL is the production database and the existing pgvector image remains
   available but unused until it is evaluated later;
4. internal records use UUIDs while provider identifiers and provenance remain
   explicit, reviewable fields;
5. user-owned records point to an ownership anchor that can accept a real auth
   subject in Phase 10;
6. the current demo uses one server-configured fictional owner and never accepts
   an owner ID from the browser;
7. route -> service -> repository -> database layering is demonstrated by the
   profile resource;
8. the profile loaded in demo bootstrap and saved from the profile form is
   durable across browser sessions;
9. migrations and repositories have fast isolated SQLite coverage plus a real
   PostgreSQL migration smoke gate when Docker is available; and
10. no ranking, live academic retrieval, authentication, AI generation, resume
    upload, opportunity ingestion, or email sending is implied.

## 2. Starting state and preservation

- Phase 4 is committed as `6f3b735` and the working tree is clean.
- FastAPI exposes a deterministic mock catalog through typed contracts, but all
  product routes are stateless.
- The frontend keeps editable workflow state in tab-scoped `sessionStorage`.
- Docker Compose already defines PostgreSQL 17 with pgvector, but Docker Desktop
  is not currently running in the audit environment.
- No database library, engine, ORM model, migration, repository, or durable
  product write exists yet.
- The owner's earlier `6138f9e` commit remains part of the baseline and will not
  be rewritten.

## 3. Scope boundary

### 3.1 Implemented in Phase 5

- async SQLAlchemy engine and one request-scoped `AsyncSession`;
- Alembic async migration environment and initial reversible migration;
- ownership, profile, academic-catalog, provenance, saved-item, draft,
  opportunity, application, and application-event tables;
- owner and profile repositories;
- profile service and typed read/update transport;
- persistent profile composition in the demo bootstrap;
- frontend profile mutation with pending, success, structured-error, and retry
  behavior;
- migration/model drift, constraint, repository, route, contract, and E2E tests;
- isolated E2E database and API port so tests cannot mutate a developer's active
  database or server.

### 3.2 Modelled but not behaviorally implemented

The schema reserves honest storage for later approved phases, but Phase 5 does
not expose CRUD or ingestion workflows for:

- papers, authors, institutions, paper topics, and provenance;
- opportunities and saved items;
- drafts and draft evidence;
- applications and immutable application events.

Those models exist now because Phase 5 owns schema design. Their business rules,
provider ingestion, UI integration, and authorization arrive in the roadmap
phases that own those behaviors.

### 3.3 Explicitly absent

- authentication or trust in a browser-provided user/owner identifier;
- authorization, tenant switching, or public profile handling;
- OpenAlex, Semantic Scholar, Crossref, ORCID, arXiv, or scraping;
- ranking, scoring, embeddings, pgvector columns, or OpenSearch;
- LLMs, LangGraph, prompt storage, or provider calls;
- automatic database creation at application startup;
- background jobs, Redis, Celery, email lookup, or sending.

## 4. Ownership and privacy boundary

`account_owners` is a data-partition anchor, not an authentication system.

- Every private mutable record has a non-null owner foreign key, directly or
  through its parent.
- The browser never sends `ownerId`.
- Demo dependencies resolve one `DEMO_OWNER_ID` from server-only settings.
- A demo owner has `kind = demo` and no external authentication subject.
- A future authenticated owner has `kind = authenticated` and a unique external
  subject supplied only after backend token verification in Phase 10.
- Until Phase 10, only fictional demo profile data is appropriate. The UI keeps
  its existing warning not to enter private or real information.
- Database URLs, passwords, profile bodies, and draft bodies are never logged.

This structure demonstrates row ownership without falsely claiming that rows
are currently protected by authentication.

## 5. Data model

```text
account_owners
  └─ student_profiles (one per owner)
       ├─ profile_interests
       ├─ profile_skills
       ├─ profile_projects
       └─ profile_preferences (zero/one)

institutions
  └─ authors
       └─ paper_authors ── papers
                              └─ paper_topics

provenance_records ── logical public entity reference

account_owners
  ├─ saved_items ── exactly one of paper | author | opportunity
  ├─ outreach_drafts ── author + draft_papers ── papers
  └─ applications ── exactly one of author | opportunity
       └─ application_events (append-only history)

opportunities remain source-linked public catalog records.
```

### 5.1 Ownership and profile

#### `account_owners`

- UUID primary key;
- owner kind: `demo` or `authenticated`;
- nullable unique external auth subject;
- created/updated timestamps;
- check constraint connecting owner kind to auth-subject presence.

#### `student_profiles`

- UUID primary key and unique non-null owner foreign key;
- display name, degree/program, institution display text, graduation year, and
  weekly availability;
- created/updated timestamps;
- graduation-year and availability constraints.

Interests and skills are child rows with normalized value, display value, and
stable position. Projects are child rows with title, summary, and position.
Preferences hold bounded JSON arrays for future location/institution and
opportunity preferences; they are not treated as professor attributes.

### 5.2 Academic catalog and provenance

#### `institutions`

- name plus normalized name;
- ROR ID, country, city, homepage/source URLs;
- last-verified timestamp;
- unique provider identifiers where known.

#### `authors`

- international display name plus normalized comparison name;
- academic title remains nullable/unknown;
- optional institution foreign key;
- OpenAlex ID, Semantic Scholar ID, ORCID, source URL, and last verification;
- each external identifier is separately unique when present.

#### `papers`

- title and normalized title, year, venue, optional abstract;
- DOI, OpenAlex ID, Semantic Scholar ID, and arXiv ID;
- evidence strength (`title-only`, `abstract`, or `full-text`);
- source URL and timestamps;
- unique external IDs when known.

`paper_authors` preserves author order and nullable corresponding-author status.
`paper_topics` preserves normalized topics and display order. No vector or score
is stored in this phase.

#### `provenance_records`

- public entity kind and internal UUID reference;
- provider/source name and required provider record ID;
- source URL, retrieval time, last verification, content hash, and field list;
- uniqueness across entity, provider, and provider record.

The polymorphic entity reference cannot have one relational foreign key. The
repository layer must validate the target; this tradeoff avoids five nearly
identical provenance tables and is documented explicitly.

### 5.3 Workflow records

#### `opportunities`

Stores the later Phase 9 public record shape: source IDs/URLs, title,
organization, location/country, work mode, funding, availability, deadline,
application URL, and verification timestamps. Unknown enum values remain
explicit.

#### `saved_items`

Contains nullable paper, author, and opportunity foreign keys plus an owner,
note, and timestamp. A database check requires exactly one target. Separate
owner-target unique constraints prevent duplicate saves.

#### `outreach_drafts` and `draft_papers`

Store owner, optional recipient author, recipient snapshots, subject/body,
generation metadata, warnings/facts JSON, explicit version, timestamps, and the
ordered supporting papers. They do not create or send email.

#### `applications` and `application_events`

Applications belong to an owner and target exactly one author or opportunity.
They keep label/source snapshots, status, notes, follow-up date, and optimistic
version. Events preserve ordered status history with from/to status and an
optional note. Repositories will append events rather than overwrite history in
the later tracker phase.

## 6. Relational rules

- Internal primary keys are UUIDs generated in application code.
- All timestamps are timezone-aware UTC and have database defaults.
- Foreign-key deletion is deliberate: private child collections cascade;
  public evidence targets use `RESTRICT` or `SET NULL` so history is not silently
  erased.
- Multi-value profile rows have unique normalized values and unique positions
  per profile.
- Paper-author and paper-topic order is unique per paper.
- External academic identifiers are nullable and individually unique.
- Status, evidence, owner-kind, availability, funding, and work-mode values use
  validated non-native enums with database check constraints. This keeps the
  initial migration portable while retaining database enforcement.
- JSON columns contain bounded lists or structured metadata, not unvalidated
  private blobs.
- Useful foreign-key, owner, status, follow-up, external-ID, and verification
  indexes are named explicitly.
- Model metadata uses a naming convention so Alembic constraints are stable.

## 7. Backend architecture

```text
HTTP request
  -> request ID middleware
  -> versioned route
  -> ProfileService
  -> OwnerRepository + ProfileRepository
  -> request-scoped AsyncSession / transaction
  -> PostgreSQL
  -> Pydantic response validation
```

Planned modules:

```text
app/
  db/base.py
  db/session.py
  db/models/
  repositories/owners.py
  repositories/profiles.py
  services/profile.py
  schemas/profile.py
  api/v1/routes/profile.py
alembic.ini
alembic/env.py
alembic/versions/<revision>_initial_persistence.py
```

One `AsyncSession` belongs to one request/transaction and is never shared across
concurrent tasks. Repositories flush but do not commit; the dependency boundary
commits successful writes and rolls back failures.

The mock discovery/draft service remains deterministic. Its bootstrap receives
the profile repository so the catalog returns the durable profile when present
and the canonical fictional default otherwise.

## 8. Profile API and frontend flow

### `GET /api/v1/demo/profile`

Returns the durable fictional-owner profile, or the canonical default when no
row has been saved. Reading does not silently create database state.

### `PUT /api/v1/demo/profile`

Accepts the existing strict student-profile contract, validates it, upserts the
owner/profile aggregate in one transaction, replaces ordered interests, skills,
and the current project, and returns the stored representation.

The API does not accept an owner ID and does not claim authentication.

### Browser state

- Bootstrap remains the initial catalog query and now resolves the durable
  profile through FastAPI.
- A compatible `sessionStorage` workflow snapshot may restore selections,
  drafts, saves, and tracker state, but never override the server profile.
- Saving the profile uses a TanStack Query mutation.
- Success updates the bootstrap cache and reducer only after the transaction
  succeeds.
- Failure keeps form input editable and shows a safe message plus request ID.
- Reset restores the last server-confirmed profile and clears local workflow
  state; it does not delete the database row.

## 9. Migrations

- Alembic is the only supported schema-change path.
- The application never calls `Base.metadata.create_all()` in production.
- `alembic upgrade head` creates a blank database from the initial revision.
- `alembic downgrade base` is tested on an isolated database.
- `alembic check` detects ORM/migration drift.
- Offline SQL generation verifies PostgreSQL DDL can be rendered without a
  running server.
- A live PostgreSQL smoke test upgrades, checks head, exercises the profile
  repository, and downgrades only an isolated test database.
- Migrations contain no private user data or environment secrets.

## 10. Dependencies

| Dependency | Scope | Reason |
| --- | --- | --- |
| `SQLAlchemy[asyncio]` | backend runtime | Typed SQLAlchemy 2 ORM, SQL expression layer, async engine, and transaction/session primitives. |
| `Alembic` | backend runtime/deployment | Reviewable, ordered, reversible schema migrations and drift checks. |
| `asyncpg` | backend runtime | SQLAlchemy-supported asyncio PostgreSQL driver; unlike Psycopg's async path, it works with Uvicorn's default Windows event loop. |
| `aiosqlite` | backend development/test | Fast isolated repository and migration tests when Docker is unavailable; it is never the declared production database. |

The async session follows current SQLAlchemy guidance: one session per logical
transaction, passed explicitly rather than a mutable global scoped session.
Alembic uses its documented async-engine bridge.

## 11. Isolated E2E strategy

Profile saving now mutates durable state, so the E2E suite must not reuse an
unknown developer API or database.

1. Build Next.js with an E2E-only API origin on port 8100.
2. Create a unique temporary SQLite database.
3. Run `alembic upgrade head` against that database.
4. Start FastAPI on 8100 with the temporary database URL.
5. Start production Next.js on 3100 and run Playwright.
6. Verify the profile survives a fresh browser context/reload.
7. Stop only owned processes and delete only the exact temporary directory.

SQLite makes the browser suite deterministic; PostgreSQL-specific confidence
comes from offline DDL plus the separate live PostgreSQL migration smoke gate.

## 12. Test strategy

### Models and migrations

- expected tables, foreign keys, indexes, checks, and uniqueness exist;
- exactly-one-target constraints reject malformed saved/application records;
- profile child ordering and normalized-value uniqueness are enforced;
- upgrade -> head -> drift check -> downgrade succeeds on isolated SQLite;
- PostgreSQL offline SQL contains UUID, foreign key, check, and index DDL;
- live PostgreSQL upgrade/check/downgrade runs when Docker is available.

### Repository and service

- missing profile returns the canonical default without a write;
- first save creates the demo owner and complete profile aggregate;
- later save updates scalar fields and replaces ordered child collections;
- one owner cannot receive two profiles;
- transaction rollback preserves the previous profile on failure;
- repository loading does not trigger implicit async lazy I/O.

### API and contract

- profile GET/PUT use the structured error/request-ID conventions;
- bootstrap returns a stored profile when present;
- invalid profile input returns field-level 422 details;
- database failures return a safe 500 without leaking URLs or SQL;
- OpenAPI and the generated TypeScript client remain current.

### Frontend and E2E

- profile save calls the generated client with validated data;
- pending, success, and structured failure states are visible;
- server profile wins over a stale browser snapshot;
- profile survives reload/new context in the isolated full-stack suite;
- the complete evidence/draft/tracker journey still works;
- responsive, keyboard, reduced-motion, and no-send checks remain green.

## 13. Quality gates

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run alembic upgrade head --sql
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

Live PostgreSQL gate, after starting Docker Desktop, uses a dedicated test
database rather than the developer database.

Manual browser QA covers profile load/save/reload, request-ID error feedback,
desktop layout, 390px layout, keyboard focus, and console warnings/errors.

## 14. Milestones

### A. Persistence foundation

- [x] Add and explain database dependencies/settings.
- [x] Add async engine/session and deterministic metadata conventions.
- [x] Add modular SQLAlchemy models and enums.

### B. Migration discipline

- [x] Add Alembic async configuration.
- [x] Generate and review the reversible initial migration.
- [x] Add migration/drift/offline PostgreSQL checks.

### C. Durable profile boundary

- [x] Add owner/profile repository protocols and SQL implementations.
- [x] Add request transaction dependency and profile service.
- [x] Add profile GET/PUT routes and compose stored profile into bootstrap.

### D. Frontend integration

- [x] Generate the updated frontend contract.
- [x] Save profile through a TanStack Query mutation.
- [x] Make the server profile authoritative over stale session state.
- [x] Preserve accessible pending, success, and failure states.

### E. Verification and teaching

- [x] Add model, migration, repository, API, adapter, and E2E tests.
- [x] Pass backend, frontend, contract, and database gates.
- [x] Verify desktop/mobile/error behavior in a browser.
- [x] Update README, API README, ROADMAP, and learning log.
- [x] Review the full diff and scan for secrets/private data.

## 15. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Ownership fields are mistaken for authentication | Keep routes under `/demo`, resolve owner server-side, document the boundary in API/UI, and defer security claims to Phase 10. |
| Async lazy loading raises runtime errors | Use eager `selectinload`, map records inside the request session, and test repository reads after flush/refresh. |
| ORM and migration drift | Check Alembic against migrated metadata and keep the migration in the same reviewed commit as every model change. |
| SQLite tests hide PostgreSQL differences | Keep types portable, render PostgreSQL offline SQL, and require a separate live PostgreSQL smoke gate before claiming PostgreSQL verification. |
| E2E mutates a developer database | Use a unique temporary database and API port; never reuse an existing server for write tests. |
| Profile state conflicts with sessionStorage | Treat the database profile as authoritative and hydrate only compatible local workflow fields. |
| Replacing child collections creates duplicates | Normalize values, enforce owner/profile uniqueness, use ordered unique constraints, and replace inside one transaction. |
| Polymorphic provenance lacks a database FK | Validate target kind/ID in repositories and document the deliberate shared-table tradeoff. |
| Initial schema becomes over-engineered behavior | Model later entities now as required, but expose only profile persistence in this phase. |
| Private values leak through logs/errors | Continue metadata-only logs and generic database error responses; test that URLs, SQL, and profile bodies are absent. |

## 16. Verification evidence

- Backend formatting, Ruff, strict mypy, OpenAPI drift, and all 18 pytest cases
  pass.
- PostgreSQL 17 passed upgrade, head verification, zero-drift inspection,
  profile save/bootstrap reload, and downgrade on a disposable database and
  role; both were removed after the smoke test.
- Frontend lint, strict TypeScript, 18 Vitest cases, production build, generated
  client drift, and production dependency audit pass.
- All five Playwright flows pass against a unique migrated SQLite database and
  owned API port; Windows process/file cleanup also exits cleanly.
- Desktop and 390px in-app browser review confirmed durable reload, no page
  overflow, accurate persistence copy, and no console warnings/errors.
- Docker Compose configuration renders successfully without changing tracked
  configuration.

## 17. Rollback

- Phase 4 remains recoverable as `6f3b735`.
- The initial migration provides a reviewed downgrade to an empty schema.
- E2E databases are disposable and isolated.
- No migration targets an existing user database during automated tests.
- Phase 5 changes are kept together for one reviewable commit after every
  available gate passes.

## 18. Completion rule

Phase 5 is complete only when the initial schema and downgrade are reviewable,
model/migration drift is checked, owner/profile repositories are transactionally
tested, the browser profile is genuinely durable through the API, the E2E suite
uses isolated state, teaching documentation is current, and no future-phase
behavior or authentication claim has been introduced.

The exact next step after acceptance is **Phase 6 — OpenAlex discovery and
normalization**: integrate the first real academic provider behind typed,
bounded, provenance-preserving clients while keeping ranking deferred.
