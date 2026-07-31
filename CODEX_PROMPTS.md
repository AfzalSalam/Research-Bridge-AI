# CODEX_PROMPTS.md

Use one prompt at a time. These are execution aids, not independent sources of
truth. `AGENTS.md`, `PROJECT_SPEC.md`, `ROADMAP.md`, and the active approved plan
take precedence. Update a prompt when those documents change.

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
LangGraph after deterministic services work, provider-independent LLM adapter,
Pydantic structured outputs, deterministic placement-release relevance,
evidence validation, and human review. Advanced ranking is post-placement.

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
- Professor results with a clearly labelled demo relevance band, evidence,
  papers, source links, confidence, and uncertainty.
- Professor detail/evidence screen.
- Internship results with source and last-verified metadata.
- Editable mock email draft customized from selected profile and paper facts,
  with visible claim-to-evidence references.
- Mock saved items and application tracker.
- Loading, empty, error, and partial-failure states.
- Responsive layouts.
- Playwright flow:
  enter topic -> search -> inspect professor -> generate/edit draft.

All people, contact information, and outcomes must be visibly labelled demo
data. No real AI, auth, database persistence, or academic clients.
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

## Prompt 6 — OpenAlex discovery and normalization

Implement Phase 6 only.

Implement OpenAlex as the first real academic source. Add honest interfaces for
Semantic Scholar, Crossref, ORCID, ROR, and arXiv without pretending an
unimplemented integration works.

OpenAlex needs typed models, async HTTPX, explicit timeout, bounded retry,
rate-limit handling, a cache interface, structured logs, partial-failure
behavior, provenance, mocked tests, and representative fixtures.

Normalize and deduplicate papers, authors, and institutions. Preserve DOI,
OpenAlex IDs, ORCID, ROR, source URLs, and retrieval timestamps. Resolve authors
and institutions sufficiently to derive candidate records later, but do not
calculate mentor relevance yet.

Deduplication priority:

1. DOI
2. OpenAlex ID
3. Semantic Scholar ID when present
4. normalized title + year
5. ORCID for author identity
6. normalized author name + institution as lower confidence

Connect real topic search to OpenAlex and show normalized paper evidence with
loading, empty, error, rate-limit, and partial-failure states. No ranking,
email generation, or LangGraph yet. Stop after Phase 6.

---

## Prompt 7 — Basic relevance and evidence

Implement Phase 7 only.

Implement:

- mentor candidates derived from supporting-paper authors;
- verified title/institution evidence where available;
- a transparent deterministic placement-release heuristic using supporting-
  paper topic relevance, recent relevant publication activity, and evidence
  completeness;
- configurable weights and visible feature contributions;
- relevance bands that do not claim research-grade ranking quality;
- evidence completeness/confidence;
- source links and retrieval/verification timestamps;
- `Unknown` availability by default;
- warnings for unsupported or stale facts;
- feature, ordering, duplicate, and evidence tests;
- actual measurements for retrieval success, duplicate rate, evidence
  coverage, unsupported-claim rate, and latency.

Do not add embeddings, pgvector search, cross-encoder reranking, or ranking
metrics in this phase. LLMs must not determine relevance. Stop after Phase 7.

---

## Prompt 8 — Evidence-grounded outreach

Implement Phase 8 only.

- Generate only after the user selects a mentor and supporting paper evidence.
- Use verified profile facts and one or two selected papers.
- Do not infer paper methods/results from titles alone.
- Produce structured subject, body, evidence references, uncertainty warnings,
  generation mode, model/provider metadata, and prompt version.
- Provide concise, formal, and enthusiastic tone options.
- Implement an editable and versioned writer-focused draft UI.
- Show claim-to-evidence mapping.
- Ask about availability unless an official source verifies it.
- Never guess contact information.
- Provide a deterministic fallback template.
- Test grounding, unsupported claims, invalid output, provider failure,
  fallback behavior, and draft versioning.
- Never automatically send email.

Stop after Phase 8.

---

## Prompt 9 — Internships and application tracker

Implement Phase 9 only.

Opportunity model includes title, organization, field, country, work mode,
funding, duration, eligibility, deadline, application link, source, last-
verified timestamp, and confidence.

Funding and work-mode values include `Unclear`. Implement official-source
ingestion first and controlled allowlisted extraction only for documented gaps.
Add stale/expired detection, source display, filters, saving, notes, follow-up,
and application statuses:

Saved, Preparing, Draft ready, Applied, Follow-up due, Response received,
Interview, Accepted, Rejected, Closed.

Store application event history and relations to mentor, paper, opportunity,
and draft where applicable. Demo data must be visibly labelled. Stop after
Phase 9.

---

## Prompt 10 — Authentication, privacy, and security

Implement Phase 10 only.

First compare suitable authentication approaches for the current architecture,
document the trade-offs, and implement the approved approach.

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
- account/data deletion path;
- security tests and threat model.

Never log resume contents, private profile text, or secrets. Stop after Phase
10.

---

## Prompt 11 — LangGraph workflow and progress

Implement Phase 11 only, after the deterministic services are complete and
tested.

Typed graph state includes search ID, profile reference, raw/expanded query,
papers, candidates, relevance features, evidence warnings, selected mentor,
selected paper evidence, draft, progress, and recoverable errors.

Nodes:

validate -> bounded query expansion -> retrieve -> normalize/deduplicate ->
resolve authors/institutions -> collect evidence -> calculate relevance ->
validate evidence -> pause for mentor/paper selection -> generate draft ->
pause for review -> complete.

Requirements:

- deterministic services remain deterministic and independently callable;
- Pydantic-validated LLM output;
- provider abstraction and versioned prompts;
- persistence/checkpointing documented;
- SSE progress without fabricated percentages;
- cancellation and partial failures;
- no automatic sending;
- node, integration, checkpoint, and progress tests.

Stop after Phase 11.

---

## Prompt 12 — Quality and observability

Implement Phase 12 only.

Complete frontend unit/component/E2E/accessibility tests; backend unit,
integration, DB, retry, auth, and graph tests.

Create placement-release reports for retrieval success, duplicate rate,
evidence coverage, unsupported-claim rate, source freshness, and latency
percentiles. Do not add advanced ranking metrics in this phase.

Add structured logs, request/search IDs, error reporting, tracing interface,
and privacy-safe LLM model/prompt/token/latency metadata.

Create a report containing actual results only. Stop after Phase 12.

---

## Prompt 13 — Deployment and portfolio release

Implement Phase 13 only.

Target:

- Next.js on Vercel.
- FastAPI on a suitable managed container/service.
- Managed PostgreSQL with pgvector capability available but not required by the
  placement heuristic.
- Redis only if required.
- S3-compatible storage.
- GitHub Actions.
- Docker local environment.
- platform secrets.
- health/readiness checks.
- migration, backup, rollback, preview/staging, production, smoke-test, and
  runbook procedures;
- deterministic, clearly labelled demo mode;
- polished README, architecture and data-flow diagrams, screenshots,
  limitations, and a concise recruiter interview demo script.

Document provider choices and current costs/limitations. Exercise the critical
live and demo journeys before declaring the placement release complete. Stop
after Phase 13.

---

## Prompt 14 — Post-placement ranking and enrichment research

Implement Phase 14 only after the placement release is complete.

- Define a versioned labelled relevance dataset and annotation guide.
- Establish the basic heuristic as the baseline.
- Evaluate PostgreSQL full-text search and pgvector semantic retrieval.
- Add an embedding-provider interface and reproducible embedding metadata.
- Tune deterministic features without leaking evaluation labels.
- Evaluate an optional cross-encoder reranker behind a feature flag.
- Report Recall@5, Recall@10, MRR, nDCG@10, duplicate rate, evidence coverage,
  unsupported-claim rate, and latency percentiles.
- Expand Semantic Scholar, Crossref, ORCID, ROR, and arXiv enrichment only with
  typed clients, provenance, rate-limit handling, partial failures, and tests.
- Adopt additional complexity only when the evaluation shows a measurable
  improvement and document negative results honestly.

LLMs must never invent relevance scores. Stop after Phase 14.

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
