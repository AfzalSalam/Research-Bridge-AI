# AGENTS.md

## Project

**Research Bridge AI** is a full-stack academic discovery and research-opportunity platform. It helps students:

- discover relevant academic papers;
- identify and rank suitable professors;
- inspect evidence behind each match;
- find verified research internships;
- generate editable, evidence-grounded outreach drafts;
- save opportunities and track applications.

## Product principles

1. Evidence before generation.
2. Deterministic scoring before LLM explanation.
3. Human approval before using an email draft.
4. Academic APIs before scraping.
5. Unknown facts remain unknown.
6. Professional, accessible UI over excessive animation.
7. Modular monolith before microservices.
8. Measured retrieval quality over impressive-sounding agent labels.

## Required reading

Before editing code, read:

- `PROJECT_SPEC.md`
- `ROADMAP.md`
- the active plan under `docs/plans/`

For any multi-file or cross-subsystem task, create/update an execution plan first.

## Teaching requirement

The repository owner is learning while building. After every phase, update
`docs/LEARNING_LOG.md` with:

- what was built;
- why it exists;
- concepts introduced;
- data flow;
- important files;
- how to run/test it;
- common errors and debugging;
- limitations;
- next step.

Do not only output commands or code.

## Scope control

- Implement one approved phase at a time.
- Do not implement future phases early.
- Do not rewrite working architecture without an explicit reason.
- Explain every new dependency.
- Next.js is the frontend; FastAPI is the main backend.
- Do not add CrewAI or AutoGen to the production workflow.
- LangGraph is the selected orchestrator.
- Do not add OpenSearch before PostgreSQL full-text search and pgvector are working and evaluated.
- Do not add Celery before synchronous search works correctly.

## Frontend

Stack:

- Next.js App Router
- React
- TypeScript strict mode
- Tailwind CSS
- shadcn/ui
- TanStack Query
- React Hook Form
- Zod
- Motion only where it improves understanding
- Lucide icons

Rules:

- Prefer Server Components unless interaction requires a Client Component.
- Use `"use client"` only where needed.
- Avoid `any`.
- Use TanStack Query for server state and React Hook Form + Zod for forms.
- Use semantic HTML, keyboard navigation, visible focus, accessible labels, and reduced-motion support.
- Every data screen needs loading, empty, error, and partial-failure states.
- Avoid continuous blur, particle, cursor-follow, and heavy card animations.
- Do not regenerate the entire frontend after the design system is approved.
- Use design tokens instead of arbitrary colors and spacing.
- Never expose secrets in `NEXT_PUBLIC_*`.

## Backend

Stack:

- Python
- FastAPI
- Pydantic
- SQLAlchemy 2
- Alembic
- HTTPX
- uv
- PostgreSQL
- pgvector
- Redis later

Architecture:

`route -> service -> repository/external client -> database/API`

Rules:

- Routes contain transport logic, not business logic.
- Use typed Pydantic request/response schemas.
- Use Python type hints throughout.
- Use async HTTPX for external APIs.
- Configure explicit timeouts, bounded retries, rate-limit handling, and structured errors.
- Every schema change requires an Alembic migration.
- Store provenance and external IDs such as DOI, OpenAlex ID, Semantic Scholar ID, ORCID, and ROR.
- Never silently catch broad exceptions.
- Never log secrets or private resume contents.

## AI and retrieval

Use deterministic code for:

- validation;
- API retrieval;
- filtering;
- normalization;
- deduplication;
- score calculation;
- database writes;
- permissions and status transitions.

Use an LLM only for:

- bounded query expansion;
- carefully bounded ambiguous identity assistance;
- evidence-grounded explanations;
- evidence-grounded email drafting.

Rules:

- LLMs must not invent numeric ranking scores.
- Every recommendation retains evidence and source URLs.
- Unknown funding, work mode, availability, or contact details remain unknown.
- LLM outputs must be structurally validated.
- Prompts must be versioned.
- Email drafts only use verified student and professor facts.
- The user must select a professor and review the draft.
- Never mass-send or automatically send emails.

## Data sources

Preferred order:

1. OpenAlex
2. Semantic Scholar
3. Crossref
4. ORCID
5. arXiv
6. Controlled public university/lab extraction only for gaps

Do not scrape Google Scholar.

Controlled extraction must respect site rules and rate limits, use a domain
allowlist, protect against SSRF, retain source URLs, and record last-verified
timestamps.

## Quality gates

Frontend:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

Backend:

```bash
uv run ruff check .
uv run mypy app
uv run pytest
```

Full-stack critical flows should use Playwright.

Ranking must eventually report:

- Recall@5 and Recall@10
- MRR
- nDCG@10
- duplicate rate
- evidence coverage
- unsupported-claim rate
- latency percentiles

## Git discipline

- Inspect branch and working tree before editing.
- Preserve unrelated user work.
- Review the full diff before completion.
- Never commit `.env`, secrets, API keys, resumes, or private generated data.
- Create clear commits after each accepted phase.

## Completion report

At the end of every task provide:

1. What changed.
2. Files changed.
3. Concepts involved.
4. Tests/commands and outcomes.
5. Known limitations or mocked behavior.
6. Exact next step.
