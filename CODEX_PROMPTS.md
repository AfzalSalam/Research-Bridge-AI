# CODEX_PROMPTS.md

Use one prompt at a time.

---

## Prompt 0 — Master handoff and repository audit

You are the lead engineer responsible for completing Research Bridge AI in
this repository.

First inspect the repository and read:

- AGENTS.md
- PROJECT_SPEC.md
- ROADMAP.md
- all existing source code and configuration

Do not begin broad implementation immediately.

Your first task:

1. Audit the current repository.
2. Identify what exists, what is stale, what conflicts with the approved
   architecture, and what can be reused.
3. Check Git status and preserve all user work.
4. Create `docs/plans/phase-00-audit-and-foundation.md` with:
   current state, target state, assumptions, risks, files likely to change,
   milestone checklist, validation commands, rollback strategy, and only
   genuinely blocking questions.
5. Recommend whether to migrate, archive, or selectively reuse current code.
6. Do not write application code during this first task.
7. Explain all important concepts clearly.

Selected stack:

Frontend:
Next.js App Router, React, TypeScript strict, Tailwind, shadcn/ui,
TanStack Query, React Hook Form, Zod, restrained Motion, Lucide.

Backend:
Python, FastAPI, Pydantic, SQLAlchemy 2, Alembic, HTTPX, uv.

Data:
PostgreSQL, pgvector, Redis later, private object storage later.

AI:
LangGraph, provider-independent LLM adapter, Pydantic structured outputs,
deterministic ranking, optional cross-encoder reranking, evidence validation,
human review.

Sources:
OpenAlex primary, Semantic Scholar, Crossref, ORCID, arXiv, and controlled
public lab/university extraction only where needed.

Do not add CrewAI, AutoGen, a Next.js backend, OpenSearch, Celery,
authentication, or cloud infrastructure during foundation.

At the end report repository findings, migration recommendation, risks,
blockers, and the exact next prompt.

---

## Prompt 1 — Foundation

Implement Phase 1 only.

Read AGENTS.md and the approved phase-00 plan. Create/update
`docs/plans/phase-01-foundation.md` before editing code.

Required outcome:

- Next.js App Router frontend with TypeScript strict mode.
- FastAPI backend managed by uv.
- Docker Compose for PostgreSQL with pgvector.
- `GET /api/v1/health`.
- Frontend health display using a typed API client.
- `.env.example` files and Windows-friendly README.
- CORS for local development.
- Frontend lint, typecheck, test, and build scripts.
- Backend Ruff, mypy, and pytest.
- At least one frontend test and one backend health test.
- `docs/LEARNING_LOG.md` explaining monorepo, frontend/backend separation,
  environment variables, CORS, containers, health checks, package managers,
  linting, type checking, and tests.

Do not implement business features, database business tables, academic APIs,
LangGraph, authentication, or deployment.

Run all checks and fix failures. Stop after Phase 1.

---

## Prompt 2 — Design system and app shell

Implement Phase 2 only. Create/update its ExecPlan first.

If Figma MCP is connected and an approved Research Bridge AI file exists,
inspect it and map its tokens. Otherwise implement a coherent professional
academic design without blocking.

Implement:

- design tokens, typography, and spacing;
- Tailwind + shadcn/ui;
- accessible Button, Input, Select, Card, Badge, Dialog/Drawer, Tabs,
  Tooltip, Skeleton, Toast, and Table;
- responsive navigation and routes for landing, search, professors,
  internships, profile, saved, applications, and settings;
- loading, error, not-found, and empty states;
- component gallery or Storybook;
- keyboard/focus behavior and reduced-motion support.

No backend features or real data. Add tests and run all quality gates.
Update the learning log. Stop after Phase 2.

---

## Prompt 3 — Typed mock product flow

Implement Phase 3 only. Create/update its ExecPlan first.

Using typed fixtures only:

- Professor Discovery and Internship modes.
- Research topic, country, work-mode, and separate funding filters.
- Funding values include Any, Paid, Unpaid, Stipend, Funding unclear.
- Search loading/progress state.
- Professor results with score breakdown, evidence, papers, source links,
  confidence, and uncertainty.
- Professor detail/evidence screen.
- Internship results with source and last-verified metadata.
- Editable mock email draft.
- Mock saved items and application tracker.
- Loading, empty, error, and partial-failure states.
- Responsive layouts.
- Playwright flow:
  enter topic -> search -> inspect professor -> generate/edit draft.

No real AI, auth, database persistence, or academic clients.
Avoid heavy continuous animation. Run all checks. Stop after Phase 3.

---

## Prompt 4 — Modular backend and contracts

Implement Phase 4 only.

Implement:

- FastAPI routers under `/api/v1`;
- pydantic-settings configuration;
- structured errors, request IDs, and logging;
- CORS from configuration;
- request/response schemas;
- contracts for health, professor search, internship search, professor detail,
  email drafts, saved items, and applications;
- mock services behind interfaces;
- OpenAPI export;
- generated or verified TypeScript API types/client;
- frontend using the mock backend without changing behavior;
- contract and integration tests.

Architecture: route -> service -> repository/client interface.

No academic APIs or database business tables yet.
Run all checks. Stop after Phase 4.

---

## Prompt 5 — Database and profile

Implement Phase 5 only.

Use SQLAlchemy 2 and Alembic for:

- student profiles;
- research interests;
- skills and profile-skill relation;
- projects;
- preferences;
- papers;
- authors;
- institutions;
- paper-author relation;
- provenance/evidence;
- saved items;
- drafts;
- applications and events.

Requirements:

- UUID internal IDs where appropriate;
- timestamps, constraints, indexes;
- DOI/OpenAlex/S2/ORCID/ROR fields;
- migration up/down;
- repository layer;
- profile CRUD and frontend integration;
- no resume binary in PostgreSQL;
- ownership fields;
- migration/repository/API tests.

Explain normalization, keys, relations, migrations, transactions, indexes,
repositories, and provenance. Stop after Phase 5.

---

## Prompt 6 — Academic sources

Implement Phase 6 only.

Implement OpenAlex as the primary real source. Add honest, tested interfaces
for Semantic Scholar, Crossref, ORCID, and arXiv without pretending missing
credentials/integrations work.

Each client needs typed models, async HTTPX, timeout, bounded retry,
rate-limit handling, cache interface, structured logs, partial-failure
behavior, provenance, mocked tests, and representative fixtures.

Normalize papers/authors/institutions.

Deduplication priority:

1. DOI
2. OpenAlex ID
3. Semantic Scholar ID
4. normalized title + year
5. ORCID
6. normalized author name + institution as lower confidence

Connect real topic search to OpenAlex and show normalized papers.
No ranking or LangGraph yet. Stop after Phase 6.

---

## Prompt 7 — Retrieval and ranking

Implement Phase 7 only.

Implement:

- professor candidates from paper authors;
- institution/research evidence;
- PostgreSQL full-text retrieval;
- pgvector semantic retrieval;
- embedding provider interface;
- deterministic features and configurable weights;
- score breakdown;
- evidence completeness/confidence;
- warnings for unverified availability/funding/work mode;
- optional disabled-by-default reranker interface;
- feature tests;
- labelled evaluation fixture;
- Recall@K, MRR, and nDCG@10 scripts.

LLMs must not determine scores. Show actual evidence and score breakdown in
the frontend. Stop after Phase 7.

---

## Prompt 8 — LangGraph and progress

Implement Phase 8 only.

Typed graph state includes search ID, profile, raw/expanded query, papers,
candidates, ranking features, ranked results, evidence warnings, selected
professor, draft, progress, and recoverable errors.

Nodes:

validate -> expand query -> retrieve -> normalize/deduplicate ->
resolve authors/institutions -> collect evidence -> calculate features ->
optional rerank -> validate evidence -> explanations ->
pause for selection -> generate draft -> pause for review -> complete.

Requirements:

- deterministic services remain deterministic;
- Pydantic-validated LLM output;
- provider abstraction;
- versioned prompts;
- persistence/checkpointing documented;
- SSE progress;
- cancellation and partial failures;
- no automatic sending;
- node, integration, and progress tests.

Stop after Phase 8.

---

## Prompt 9 — Evidence-grounded email drafts

Implement Phase 9 only.

- Generate only after professor selection.
- Structured subject, body, evidence references, uncertainty warnings,
  model/provider metadata, and prompt version.
- Concise, formal, and enthusiastic tone options.
- Editable and versioned draft UI.
- Claim-to-evidence mapping.
- No invented facts or availability.
- Deterministic fallback template.
- Tests for grounding, invalid output, provider failure, and fallback.
- Never automatically send.

Stop after Phase 9.

---

## Prompt 10 — Internships and tracker

Implement Phase 10 only.

Opportunity model includes title, organization, field, country, work mode,
funding, duration, eligibility, deadline, application link, source,
last verified date, and confidence.

Funding statuses:
Paid, Unpaid, Stipend, Funding unclear.

Implement stale/expired detection, source display, filters, saving, and
application statuses:

Saved, Preparing, Draft ready, Applied, Follow-up due, Response received,
Interview, Accepted, Rejected, Closed.

Add event history, notes, follow-up, and relations to professor/paper/draft.
Demo data must be visibly labelled. Stop after Phase 10.

---

## Prompt 11 — Authentication and security

Implement Phase 11 only.

First compare suitable auth approaches for the current architecture and
document the decision. Then implement the approved approach.

- protected frontend routes;
- backend identity/token validation;
- user-row isolation;
- private resume object storage with signed access;
- no frontend secrets;
- rate limiting;
- body/file limits and validation;
- SSRF protection and extraction allowlist;
- safe rendering;
- audit-relevant events;
- deletion path;
- security tests and threat model.

Never log resume contents or secrets. Stop after Phase 11.

---

## Prompt 12 — Quality and observability

Implement Phase 12 only.

Complete frontend unit/component/E2E/accessibility tests; backend unit,
integration, DB, retry, auth, and graph tests.

Create retrieval evaluation for Recall@5/10, MRR, nDCG@10, duplicate rate,
evidence coverage, unsupported-claim rate, and latency percentiles.

Add structured logs, request/search IDs, error reporting, tracing interface,
and privacy-safe LLM model/prompt/token/latency metadata.

Create a report containing actual results only. Stop after Phase 12.

---

## Prompt 13 — Deployment

Implement Phase 13 only.

Target:

- Next.js on Vercel.
- FastAPI on a suitable managed container/service.
- Managed PostgreSQL with pgvector.
- Redis only if required.
- S3-compatible storage.
- GitHub Actions.
- Docker local environment.
- platform secrets.
- health/readiness checks.
- migration, backup, rollback, preview/staging, production, smoke-test, and
  runbook procedures.

Document provider choices and costs/limitations. Stop after Phase 13.

---

## Review Gate — paste after every phase

Review the current phase against AGENTS.md, the active ExecPlan, the product
specification, roadmap, and full Git diff.

Do not start the next phase.

1. Inspect the full diff and Git status.
2. Find unfinished TODOs, mocked production behavior, duplicate logic,
   type errors, schema drift, inaccessible UI, missing validation,
   unsupported claims, and secrets.
3. Confirm routes contain no business logic.
4. Confirm frontend and OpenAPI/Pydantic schemas agree.
5. Confirm every AI-generated claim is bounded by evidence.
6. Run all applicable lint, format, type-check, test, E2E, migration,
   and production-build commands.
7. Fix failures rather than only reporting them.
8. Update the ExecPlan and `docs/LEARNING_LOG.md`.
9. Report implemented behavior, files changed, concepts, commands/results,
   limitations/mocks, security/data-quality concerns, and the exact next prompt.

Do not claim completion if required checks fail.
