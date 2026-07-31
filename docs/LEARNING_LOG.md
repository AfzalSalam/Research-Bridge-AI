# Learning Log

Append after every phase.

## 2026-07-31 — Phase 00: Audit and foundation planning

### What was built

No application code was built. The repository, Git state, local toolchain,
product documents, and Figma Make prototype were audited. A Phase 00 execution
plan now records the current state, approved placement-release direction,
target architecture, design recommendations, risks, validation, and rollback
strategy. After approval, `PROJECT_SPEC.md`, `ROADMAP.md`, `START_HERE.md`, and
`CODEX_PROMPTS.md` were reconciled so the placement release and post-placement
ranking research are no longer mixed together.

### Why it exists

The repository contained only planning documents and had no commits. Starting
implementation without recording that baseline would make it easy to mix stale
requirements, generated prototype code, and new architecture. The audit turns
those assumptions into reviewable decisions before code exists.

### Concepts introduced

- **Greenfield repository:** a project with no existing application code to
  migrate.
- **Source of truth:** the document or artifact that wins when instructions
  disagree. Active plans, the project specification, and engineering rules must
  agree before implementation.
- **Modular monolith:** one deployable backend organized into clear modules,
  giving good separation without early microservice overhead.
- **Provenance:** the source URL, external identifier, and verification time
  retained with a fact.
- **Deterministic versus generative work:** code retrieves, validates, scores,
  and stores facts; an LLM only performs bounded explanation or drafting from
  those facts.
- **Human-in-the-loop:** email generation pauses for mentor selection and the
  draft remains editable; the system never sends it automatically.
- **Responsive task flow:** mobile may use a sequence of focused screens even
  when desktop uses a master-detail workspace.

### Data flow

There is no runtime data flow yet. The planned flow is:

```text
student profile + topic
  -> Next.js UI
  -> typed FastAPI contract
  -> deterministic service
  -> academic API/database with provenance
  -> evidence-backed mentor result
  -> user selection
  -> bounded grounded draft
  -> user review/save/copy
```

### Important files

- `AGENTS.md`: engineering and teaching rules.
- `PROJECT_SPEC.md`: current product requirements that need placement-boundary
  reconciliation.
- `ROADMAP.md`: original implementation sequence that needs a release gate.
- `CODEX_PROMPTS.md`: original prompt pack; useful as a seed but not an
  authority when it conflicts with an approved plan.
- `docs/plans/phase-00-audit-and-foundation.md`: complete audit and proposed
  foundation plan.

### How to run and test it

Phase 00 has no application tests. Inspect the documentation baseline with:

```powershell
git status --short --branch
rg --files -uu -g '!.git/**'
git diff --check
```

### Common errors and debugging

- `git log` fails because `main` has no commits. This is expected until the
  documentation baseline is accepted and committed.
- PowerShell can block `npm.ps1`; use `npm.cmd` for project scripts on this
  machine.
- Node 26 is installed but is not the intended project runtime; use Node 24 LTS.
- Python 3.14 is the default, but Python 3.13 should be pinned for the backend.
- Docker CLI exists, but the daemon was not running during the audit and the
  current Docker user config reported an access error.

### Limitations

- No application, database, API, tests, CI, or deployment exists yet.
- The Figma Make prototype was audited as a visual reference; its Vite code was
  not imported.
- The documentation is reconciled, but it describes planned behavior rather
  than an implemented application.

### Next step

Prepare and approve `docs/plans/phase-01-foundation.md`, then implement only the
reproducible frontend/backend/database foundation and its quality gates.

---

## YYYY-MM-DD — Phase name

### What was built

### Why it exists

### Concepts introduced

### Data flow

### Important files

### How to run and test it

### Common errors and debugging

### Limitations

### Next step
