# Phase 00 — Repository Audit and Foundation Plan

**Status:** Complete

**Prepared:** 2026-07-31

**Approved:** 2026-07-31

**Scope:** Documentation and planning only; no application code

## 1. Objective

Establish a trustworthy starting point for Research Bridge AI before creating
the frontend or backend. This phase records what is actually in the repository,
reconciles the latest product decisions, audits the Figma Make prototype, and
defines a safe first implementation phase.

The immediate implementation goal is a placement-ready full-stack and AI
portfolio product. The long-term goal remains a high-quality academic discovery
platform. Advanced ranking research is deliberately postponed until after the
placement release; it must not block a strong, deployable core product.

## 2. Repository evidence

Audit performed from `C:\Users\afzal\Desktop\Research-Bridge AI`.

### Git state

- Branch: `main`.
- The repository has no commits and no valid `HEAD` yet.
- No Git remote is configured.
- Every existing project file is untracked.
- No files were deleted, moved, staged, or committed during this audit.
- Git is configured with `core.autocrlf=true`; line-ending consistency should
  be enforced with a repository `.gitattributes` during foundation.

This means there is no historical codebase to migrate and no rollback point.
The first accepted phase should create a clean baseline commit before feature
work begins.

### Existing files

| Path | Current purpose | Audit decision |
| --- | --- | --- |
| `AGENTS.md` | Engineering, safety, architecture, and teaching rules | Reuse as the primary engineering policy. It is detailed and largely aligned with the approved architecture. |
| `PROJECT_SPEC.md` | Product journeys, MVP, advanced scope, and result fields | Reuse selectively, then revise. Its main idea is sound, but the placement-release boundary and email-personalization requirements need to be explicit. |
| `ROADMAP.md` | Original phases 0–13 | Reuse selectively, then revise. It needs a placement-release gate and must separate a basic heuristic from post-placement ranking research. |
| `START_HERE.md` | AI-assisted development workflow | Reuse as contributor guidance after its references match the approved roadmap. |
| `CODEX_PROMPTS.md` | Phase-by-phase prompt pack | Treat as a planning seed, not an authority. Several prompts will become stale when the roadmap is revised; archive the original or regenerate it only after the plans are approved. |
| `docs/LEARNING_LOG.md` | Empty learning-log template | Reuse and append to after every phase. |

### Source code and configuration

There is currently:

- no Next.js application;
- no FastAPI application;
- no package manifest or lockfile;
- no Python project or lockfile;
- no database schema or migration;
- no Docker Compose file;
- no environment example;
- no test, lint, type-check, build, CI, or deployment configuration;
- no application assets copied from Figma.

The repository is therefore a documentation-only greenfield project, not a
partially implemented application.

### Local toolchain

| Tool | Observed state | Foundation decision |
| --- | --- | --- |
| Node.js | `v26.4.0` | Do not standardize on this non-LTS version. Pin Node 24 LTS for the project. |
| npm | `11.17.0` | Usable through `npm.cmd` on this Windows system; PowerShell may block `npm.ps1`. |
| Python | 3.14 default; 3.13 also installed | Pin Python 3.13 for library compatibility and reproducibility. |
| uv | `0.11.21` | Reuse as the Python package and environment manager. |
| Docker CLI | `29.6.1` | Installed, but Docker Desktop/daemon was not running and the user Docker config was unreadable during the audit. Validate before database work. |

## 3. Approved product direction

### Placement-release story

The product should demonstrate a coherent engineering narrative that a final-
year BTech student can explain in an interview:

1. A student creates a structured academic profile.
2. The student searches for a research topic.
3. The backend retrieves papers from academic APIs, beginning with OpenAlex.
4. Deterministic services normalize papers, resolve authors and institutions,
   deduplicate records, and retain provenance.
5. A simple, transparent relevance heuristic orders candidates and exposes its
   evidence. It is not presented as a research-grade ranking model.
6. The student inspects the papers and facts behind a mentor suggestion.
7. Only after choosing a mentor, the student generates an editable email draft
   that refers to selected, verified publications and verified profile facts.
8. The student reviews, copies, saves, and tracks the opportunity. The product
   never sends the email automatically.

This is sufficiently complex for full-stack and AI interviews because it
contains real API integration, normalization, provenance, typed contracts,
database design, deterministic retrieval, bounded LLM use, human approval,
testing, security, and deployment without relying on inflated “agent” claims.

### Placement release versus later research

**Placement release includes:**

- live deployed application and a clearly labelled demo mode;
- global English-language search with international metadata preserved;
- structured profiles for bachelor’s and master’s STEM students;
- paper-first mentor discovery with source links and uncertainty;
- a basic deterministic relevance heuristic and explainable evidence;
- custom evidence-grounded outreach drafts;
- verified internship records, saved items, and application tracking;
- authentication and private user data before public deployment;
- accessibility, responsive behavior, tests, observability, and a demo script.

**Post-placement work includes:**

- learned or cross-encoder reranking;
- pgvector tuning beyond the evaluated need of the core search;
- labelled ranking datasets and full Recall@K, MRR, and nDCG research;
- large-scale source enrichment and background refresh infrastructure;
- any claim of production-grade ranking quality.

Postponing advanced ranking is scope discipline, not a reduction in quality.
The placement version must still measure retrieval, evidence coverage,
duplicate rate, unsupported claims, and latency.

## 4. Target architecture

Use a modular monorepo and a modular monolith, not microservices:

```text
browser
  -> Next.js App Router frontend
      -> typed API client generated or checked against OpenAPI
          -> FastAPI route
              -> service
                  -> repository or academic API client
                      -> PostgreSQL / OpenAlex / enrichment source
```

### Frontend

- Next.js App Router, React, and strict TypeScript.
- Tailwind CSS and shadcn/ui foundations using project-owned design tokens.
- TanStack Query for server state.
- React Hook Form and Zod for forms.
- Lucide icons and restrained motion with reduced-motion support.
- Server Components by default; Client Components only for interaction.

### Backend

- Python 3.13, FastAPI, Pydantic, SQLAlchemy 2, Alembic, and async HTTPX.
- uv for dependency and environment management.
- Layering: `route -> service -> repository/external client`.
- Versioned `/api/v1` contracts, structured errors, request IDs, and explicit
  timeouts/retries.

### Data and AI

- PostgreSQL first; enable pgvector in the development database so it is
  available later, but do not build the advanced ranking system early.
- OpenAlex is the first real academic source. Semantic Scholar, Crossref,
  ORCID, ROR, and arXiv are enrichment sources added behind interfaces.
- Deterministic code owns retrieval, validation, normalization,
  deduplication, relevance calculation, permissions, and persistence.
- An LLM is restricted to bounded query expansion, grounded explanations, and
  grounded email drafting with structurally validated output.
- LangGraph may orchestrate the proven workflow and human-review checkpoints;
  it must not replace ordinary service logic.

## 5. Figma Make audit

Design inspected from the Figma Make file **Research Bridge AI Prototype**:

<https://www.figma.com/make/BIzf1tX38n2FV1F9SIhHZ0/Research-Bridge-AI-Prototype?p=f&t=DqQTtVIDwyg9FR4P-0>

The Make source is a Vite/React prototype. It is a visual and interaction
reference only. Its generated application code should not be copied as the
Next.js foundation.

### Reusable design decisions

- Premium editorial-academic direction instead of a generic SaaS dashboard.
- Warm neutral canvas around `#fcfaf8` / `#fdfbf7`.
- Source Serif 4-style display typography paired with a clean Manrope-style UI
  sans serif.
- Teal for evidence, verification, and selected state; indigo for brand and
  intellectual emphasis.
- Hairline dividers, generous whitespace, flat lists, and restrained corners
  instead of a page full of floating cards.
- Master-detail mentor workspace on wide screens.
- Writer-focused email editor with a separate evidence checklist.
- Meaningful progress steps instead of fabricated percentages.

### Recommended accent system

Keep teal and indigo as the only brand accents. Add warm amber only as a
semantic color for “needs verification,” “pending,” or “uncertain.” Amber is
not a third decorative brand gradient. Use red only for destructive actions or
errors and green only for genuinely verified/success states.

### Claims that must be corrected before production

The prototype includes attractive but unsupported sample claims. Production
copy and data models must not present them as facts:

- “verifying availability” and “Verified Active” require an official source
  URL and a last-verified timestamp;
- “Accepting Students” remains `Unknown` unless explicitly confirmed;
- “Top 5% of candidates” is an unsupported ranking claim for the placement
  release;
- “~40% response rate” must be removed unless based on private, consented,
  statistically meaningful data;
- mentoring history must not be inferred from publication history;
- `example.edu` contact information must be visibly labelled demo data;
- “Top 100” institution filtering is undefined and should not be a default;
- example graduation years and other demo metadata must not be stale.

### Responsive issues observed

- The mobile wordmark wraps to two lines while the portal action consumes much
  of the header; use a compact wordmark and an accessible menu or bottom
  navigation.
- Hidden desktop navigation has no visible mobile replacement.
- Search headings can appear clipped after navigation because scroll position
  is retained; route changes must restore the appropriate focus and scroll.
- The search input and button compete for width, truncating the prompt text.
- The desktop mentor master-detail layout creates horizontal overflow.
- The outreach editor is not usable at 390 px: its toolbar, subject, and editor
  overflow horizontally and the evidence panel is not presented in a clear
  mobile order.

### Responsive implementation model

- **Mobile:** one task per screen. Results list -> mentor detail -> draft;
  evidence becomes a collapsible section or bottom sheet. Primary actions may
  be sticky but must not hide content.
- **Tablet:** two-pane layouts only when each pane retains a useful minimum
  width; otherwise follow the mobile drill-down model.
- **Desktop:** master-detail mentor workspace with independently scrollable
  regions, no page-level horizontal scroll, and a readable line length.
- Test at minimum at 390 px, 768 px, 1024 px, and 1440 px, including 200% zoom,
  keyboard-only use, and reduced motion.

## 6. Migration recommendation

**Recommendation: selectively reuse and migrate; do not archive everything and
do not import the Figma Make app wholesale.**

1. Preserve `AGENTS.md` and the learning log as reusable project controls.
2. Migrate `PROJECT_SPEC.md` into a placement-release specification plus a
   clearly separated post-placement section.
3. Migrate `ROADMAP.md` to include a placement release gate and move advanced
   ranking behind it.
4. Preserve the current `CODEX_PROMPTS.md` until the new roadmap is approved,
   then archive it as the original prompt pack or regenerate it to match the
   approved plans. Do not let it override an active plan.
5. Reuse the Figma prototype’s visual language, information hierarchy, and
   interaction ideas. Rebuild components intentionally in Next.js with the
   approved stack, accessibility, real states, and typed data.
6. Create the application as a clean monorepo foundation because no reusable
   application code exists.

## 7. Recommended roadmap correction

Keep the one-phase-at-a-time discipline, with these release tracks:

1. Foundation and reproducible tooling.
2. Design tokens, accessible component primitives, and responsive shell.
3. Typed mock journey matching the approved Figma direction.
4. FastAPI contracts and generated/verified TypeScript client.
5. PostgreSQL schema, profile, saves, drafts, and application state.
6. OpenAlex retrieval, normalization, provenance, and candidate resolution.
7. Basic deterministic relevance heuristic and evidence validation.
8. Grounded custom email drafting and human review.
9. Verified internship ingestion and application tracker.
10. Authentication, isolation, privacy, and controlled extraction security.
11. LangGraph workflow/progress only after the underlying services work.
12. Quality, accessibility, observability, and retrieval/data-quality reports.
13. Deployment, demo mode, portfolio documentation, and interview demo script.
14. Post-placement advanced ranking, multi-source enrichment, and evaluation.

`PROJECT_SPEC.md`, `ROADMAP.md`, and the executable prompt pack should be
reconciled to this sequence before the affected implementation phase starts.

## 8. Phase 1 implementation boundary

The next approved implementation phase should create foundation only:

- `apps/web`: minimal Next.js App Router application with strict TypeScript;
- `apps/api`: minimal FastAPI application managed by uv;
- a versioned `GET /api/v1/health` endpoint;
- a typed frontend health check;
- local PostgreSQL with pgvector through Docker Compose;
- environment examples with no secrets;
- lint, format, type-check, unit-test, and production-build commands;
- Windows-friendly root documentation;
- CI-ready project structure without deploying anything.

It must not add business tables, OpenAlex, mentor matching, LLMs, LangGraph,
authentication, internship extraction, or production infrastructure.

### Likely Phase 1 files

```text
/
  .editorconfig
  .gitattributes
  .gitignore
  .nvmrc or .node-version
  README.md
  compose.yaml
  package.json
  apps/
    web/
      ...Next.js foundation...
    api/
      pyproject.toml
      uv.lock
      app/
      tests/
  docs/
    plans/phase-01-foundation.md
    LEARNING_LOG.md
```

The exact generated files should be recorded in the Phase 1 execution plan
before application code is written.

## 9. Assumptions and decisions deferred safely

### Assumptions

- The project remains a monorepo containing one frontend and one backend.
- The user wants both a real deployed mode and a deterministic demo mode.
- English is the first UI language, while international names and metadata are
  preserved correctly.
- The placement release prioritizes explainability, trustworthy evidence, and
  a polished workflow over research-grade ranking novelty.
- The Figma prototype is approved as direction, not as pixel-perfect code.

### Non-blocking deferred decisions

- LLM provider and exact model: choose behind an adapter when the grounded
  drafting phase begins.
- Authentication provider: compare options during the security phase.
- Cloud vendors and costs: decide during deployment using current pricing and
  service constraints.
- Final ranking method and labelled dataset: post-placement research phase.
- Redis/background jobs: add only after measured need.

There are no genuinely blocking questions for Phase 1.

## 10. Risks and mitigations

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| Building every feature before validating the journey | Produces a broad but shallow portfolio | Complete and review one vertical phase at a time. |
| Copying Figma Make code | Conflicts with Next.js architecture and hides design debt | Treat it as reference; rebuild with tokens and tested primitives. |
| Unsupported academic claims | Damages user trust and recruiter credibility | Store provenance, timestamps, confidence, and explicit unknown states. |
| Overengineering with “agents” | Makes the project hard to explain and test | Keep deterministic services; use LangGraph only for orchestration and human gates. |
| Premature ranking research | Delays the differentiated core flow | Ship a documented heuristic; move advanced ranking after the release gate. |
| Greenfield repository with no baseline | Any edit can be lost and there is no rollback | Review this phase, then create the first clean commit before Phase 1. |
| Toolchain drift | Works on one machine but fails in CI/deployment | Pin Node 24 LTS and Python 3.13; commit lockfiles. |
| Docker unavailable | Blocks local database validation | Start Docker Desktop and verify Compose before database-dependent checks. |
| Mobile design inherited from desktop | Creates overflow and inaccessible actions | Design mobile task flows explicitly and test required widths every UI phase. |

## 11. Milestone checklist

### Phase 00 exit

- [x] Inspect Git state and preserve user work.
- [x] Read all existing repository files.
- [x] Confirm that no application code or configuration exists.
- [x] Inspect the Figma Make design and its interactive preview.
- [x] Record reusable design choices and product-trust conflicts.
- [x] Recommend selective reuse/migration.
- [x] Create this execution plan.
- [x] Update the learning log.
- [x] User approves or corrects this plan.
- [x] Establish the accepted documentation baseline in Git.

### Placement release gate

- [ ] Reproducible foundation and CI quality gates pass.
- [ ] Responsive design system and typed mock critical journey pass.
- [ ] Real OpenAlex paper discovery retains provenance and partial failures.
- [ ] Candidate evidence and basic heuristic are transparent and tested.
- [ ] Custom paper-grounded email drafting is editable and never auto-sent.
- [ ] Internship records and application state expose verification metadata.
- [ ] Authentication, isolation, privacy, and security checks pass.
- [ ] Accessibility, E2E, observability, and data-quality reports are real.
- [ ] Production deployment, demo mode, README, architecture diagram, and demo
  script are complete.

## 12. Validation commands

### Phase 00

```powershell
git status --short --branch
rg --files -uu -g '!.git/**'
git diff --check
```

Because the repository has no commit and the files are untracked, Phase 00
validation is document inspection rather than an application test suite.

### Phase 1 target checks

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
uv run ruff check .
uv run mypy app
uv run pytest
docker compose config
docker compose up -d db
```

The Phase 1 plan may add formatting or workspace-specific wrappers, but it may
not weaken these quality gates.

## 13. Rollback strategy

- Before the first commit exists, rollback is manual: review the exact created
  files and remove only Phase 00 additions after explicit approval.
- After this plan is accepted, create a baseline commit containing the
  preserved documentation and approved Phase 00 records.
- Each later phase gets its own plan, reviewed diff, passing checks, and clear
  commit. Roll back by reverting the phase commit rather than resetting or
  deleting unrelated user work.
- Never use destructive Git commands to discard local work.

## 14. Exact next step

Create and approve `docs/plans/phase-01-foundation.md`, then implement **Phase
1 — Foundation only**. Do not begin product features, academic integrations,
LLM work, authentication, or deployment during foundation.
