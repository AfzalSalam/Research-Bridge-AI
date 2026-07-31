# ROADMAP.md

## Phase 0 — Audit and plan
Inspect the repository, decide what can be reused, and create the first execution plan.

## Phase 1 — Foundation
Next.js TypeScript, FastAPI with uv, PostgreSQL + pgvector, health endpoint,
environment examples, lint/typecheck/tests/build.

## Phase 2 — Design system
Tailwind, shadcn/ui, accessible primitives, responsive app shell, routes,
loading/error/empty states, optional Figma MCP inspection.

## Phase 3 — Typed mock product flow
Professor and internship modes, filters, typed mock results, evidence UI,
editable mock draft, saved items, application tracker, Playwright flow.

## Phase 4 — Backend contracts
Modular routers, settings, errors, logging, versioned API, mock services,
OpenAPI contract, typed frontend client.

## Phase 5 — Database and profile
SQLAlchemy, Alembic, profiles, interests, skills, projects, preferences,
papers, authors, institutions, provenance, saved items, drafts, applications.

## Phase 6 — Academic sources
OpenAlex primary integration; Semantic Scholar, Crossref, ORCID, arXiv
enrichment interfaces; normalization, deduplication, retries, partial failures.

## Phase 7 — Retrieval and ranking
Professor resolution, PostgreSQL full-text search, pgvector, deterministic
features, score breakdown, optional reranker, evaluation metrics.

## Phase 8 — LangGraph
Typed state, query expansion, retrieval, resolution, ranking, evidence
validation, explanations, human selection, email draft, SSE progress.

## Phase 9 — Email drafts
Versioned prompts, structured output, evidence mapping, editing, versioning,
fallback template, no automatic sending.

## Phase 10 — Internships and tracker
Verified opportunities, last-verified metadata, funding-unclear support,
saved items, application status history and follow-ups.

## Phase 11 — Authentication and security
Identity, backend token validation, user isolation, private object storage,
rate limits, upload validation, SSRF controls, threat model.

## Phase 12 — Quality and observability
Unit/integration/E2E tests, accessibility, retrieval evaluation, structured
logs, errors, traces, prompt/model/token/latency metadata.

## Phase 13 — Deployment
Vercel frontend, managed FastAPI, PostgreSQL, optional Redis, object storage,
CI/CD, migrations, backups, runbook.
