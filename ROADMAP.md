# ROADMAP.md

Implement and review one phase at a time. Every phase requires an active plan,
the applicable quality gates, a learning-log entry, and a clear commit after
acceptance.

## Phase 0 — Audit and plan

Audit the repository and Figma prototype, decide what can be reused, establish
the architecture and product boundaries, and create the first execution plan.

**Status:** Approved and complete.

## Phase 1 — Foundation

Create the Next.js TypeScript frontend, FastAPI backend managed by uv, local
PostgreSQL with pgvector available for later use, versioned health endpoint,
typed frontend health display, environment examples, reproducible toolchain,
tests, linting, type checking, builds, and Windows-friendly documentation.

Do not implement business features.

**Status:** Complete.

## Phase 2 — Design system and responsive shell

Translate the approved Figma direction into project-owned tokens, typography,
accessible shadcn/ui-based primitives, responsive navigation, route shells,
data-state patterns, and a component gallery. Fix the mobile navigation and
overflow problems found during the Figma audit.

**Status:** Complete.

## Phase 3 — Typed mock product journey

Build the complete placement demo with typed fixtures: profile, topic search,
honest progress, mentor results, master-detail evidence, custom editable draft,
internships, saved items, application tracker, demo labels, responsive states,
and a Playwright critical flow.

No real academic APIs, AI, authentication, or database persistence.

**Status:** Complete.

## Phase 4 — Backend contracts

Add modular FastAPI routers, configuration, structured errors, request IDs,
logging, versioned request/response schemas, service interfaces, mock services,
OpenAPI export, and a generated or contract-checked TypeScript API client.
Replace frontend fixture access with the mock backend without changing behavior.

**Status:** Complete.

## Phase 5 — Database and profile

Add SQLAlchemy 2, Alembic, profiles, interests, skills, projects, preferences,
papers, authors, institutions, provenance, saved items, drafts, applications,
and application events. Implement repositories, ownership-ready fields,
constraints, indexes, migrations, and profile integration.

**Status:** Complete.

## Phase 6 — OpenAlex discovery and normalization

Integrate OpenAlex as the first real source with async HTTPX, typed models,
timeouts, bounded retries, rate-limit handling, caching interfaces, partial
failures, provenance, normalization, deduplication, author/institution
resolution, and representative fixtures.

Other academic providers remain honest interfaces until implemented.

## Phase 7 — Basic relevance and evidence

Derive mentor candidates from supporting-paper authors. Implement the
placement-release deterministic heuristic, configurable weights, feature
contributions, evidence completeness, uncertainty, source links, and tests.
Measure retrieval success, duplicate rate, evidence coverage, unsupported-claim
rate, and latency without claiming research-grade ranking quality.

## Phase 8 — Evidence-grounded outreach

Generate only after mentor and paper selection. Add versioned prompts,
structured outputs, claim-to-evidence mapping, editable draft versions,
uncertainty warnings, provider metadata, deterministic fallback templates, and
failure/grounding tests. Never send email automatically.

## Phase 9 — Internships and application tracker

Implement verified opportunity ingestion, allowlisted controlled extraction
only where needed, funding/work-mode `Unclear` states, source and last-verified
metadata, stale/expired detection, saving, application status history, notes,
and follow-up dates.

## Phase 10 — Authentication, privacy, and security

Compare and select authentication, then implement protected routes, backend
token validation, user isolation, private object storage, upload controls, rate
limits, safe rendering, SSRF protection, extraction allowlists, audit-relevant
events, deletion, security tests, and a threat model.

## Phase 11 — LangGraph workflow and progress

Orchestrate the already-tested services with typed state, honest progress,
recoverable errors, cancellation, persistence/checkpointing, SSE updates, and
human pauses for mentor selection and draft review. Deterministic logic remains
outside the LLM and independently testable.

## Phase 12 — Quality and observability

Complete unit, integration, database, contract, E2E, accessibility, security,
and failure tests. Add structured logs, request/search IDs, privacy-safe model
metadata, tracing interfaces, and reports for retrieval success, duplicate
rate, evidence coverage, unsupported claims, and latency.

## Phase 13 — Deployment and portfolio release

Deploy Next.js, FastAPI, PostgreSQL, and private object storage with CI/CD,
secrets, migrations, backups, health/readiness checks, preview/staging flow,
smoke tests, rollback and incident runbooks. Add deterministic demo mode,
architecture diagrams, screenshots, a polished README, limitations, and a
short recruiter interview demo script.

### Placement release gate

The placement release is complete only when the live and demo critical journeys
work, evidence claims are supportable, mobile and accessibility checks pass,
quality reports contain actual results, and deployment/rollback documentation
has been exercised.

## Phase 14 — Post-placement ranking and enrichment research

After the placement release, evaluate PostgreSQL full-text retrieval, pgvector,
embedding strategies, weight tuning, labelled relevance sets, cross-encoder
reranking, Recall@5/10, MRR, nDCG@10, and larger-scale multi-source enrichment.
Adopt complexity only when measurements show a benefit.
