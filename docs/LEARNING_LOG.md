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

## 2026-07-31 — Phase 01: Full-stack foundation

### What was built

A production-shaped monorepo foundation now contains a Next.js App Router
frontend, a typed FastAPI backend, a PostgreSQL/pgvector Docker Compose service,
locked JavaScript and Python dependencies, environment examples, automated
quality gates, and a working health boundary between the two applications.

The foundation page intentionally demonstrates infrastructure status rather
than pretending that mentor discovery already exists. It includes an accessible
available/unavailable state and a restrained preview of the approved warm
neutral, teal, and indigo visual direction.

### Why it exists

Every later feature depends on a trustworthy application boundary. This phase
proves that the browser-facing application and API can start independently,
communicate through a versioned contract, fail safely, and be tested before any
business complexity is introduced.

### Concepts introduced

- **Monorepo:** one repository contains separately runnable frontend and backend
  applications while sharing documentation and operational configuration.
- **Server Component:** the page requests health data on the server, so browser
  JavaScript is not required for this non-interactive state.
- **Runtime validation:** TypeScript types disappear at runtime, so an unknown
  API response is checked before the UI trusts it.
- **Discriminated union:** the frontend health result is either `available` with
  typed data or `unavailable` with a safe message; each state has known fields.
- **Application factory:** FastAPI is constructed by a function, letting tests
  provide controlled settings without mutating global configuration.
- **Versioned API:** `/api/v1/health` gives future contracts a stable namespace.
- **CORS:** the API explicitly permits the development frontend origin instead
  of allowing every website to make browser requests.
- **Lockfile:** `package-lock.json` and `uv.lock` record exact resolved versions
  so installations are reproducible.
- **Dependency risk evaluation:** narrow Next.js overrides keep vulnerable
  PostCSS and Sharp versions out of production. A development-only glob advisory
  cannot currently be patched without breaking either legacy Minimatch or the
  Next.js React lint plugin, so its controlled exposure and upgrade condition
  are documented instead of hiding a broken forced resolution.
- **Install-script allowlist:** npm may execute native package setup code only
  for the inspected, pinned resolver dependency.

### Data flow

```text
GET Next.js page
  -> server-side health client
  -> GET FastAPI /api/v1/health
  -> Pydantic HealthResponse
  -> runtime payload validation
  -> accessible available/unavailable card
```

PostgreSQL is configured but is not on this request path. The health endpoint
therefore remains useful even when the database is unavailable.

### Important files

- `package.json` and `package-lock.json`: npm workspace, root commands, runtime
  policy, security overrides, and exact dependency graph.
- `apps/web/src/app/page.tsx`: dynamic Server Component and foundation page.
- `apps/web/src/lib/api/health.ts`: typed, runtime-validated API boundary.
- `apps/web/src/components/health-card.tsx`: accessible health presentation.
- `apps/api/app/main.py`: FastAPI application factory and CORS setup.
- `apps/api/app/api/v1/routes/health.py`: versioned health transport.
- `apps/api/app/core/config.py`: typed environment settings.
- `compose.yaml`: pinned local PostgreSQL 17 and pgvector service.
- `README.md`: Windows-oriented setup, run, validation, and troubleshooting.
- `docs/plans/phase-01-foundation.md`: scope, decisions, evidence, and results.

### How to run and test it

Follow `README.md` for first-time setup. The complete gates are:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build

Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
Set-Location ../..

docker compose --env-file .env.example config --quiet
```

Run the API and web development servers in separate terminals, then open
`http://localhost:3000`. A healthy local API appears as “API available.”

### Common errors and debugging

- An engine warning means the active Node runtime is not version 24. Switch to
  the `.nvmrc` version before installing dependencies.
- TypeScript 7 is not used because the current Next.js build toolchain rejects
  its changed compiler API; the project is pinned to the supported TypeScript 6
  line.
- On this Windows machine, use `npm.cmd` if PowerShell blocks `npm.ps1`.
- If npm appears to hang while using a restricted global cache, the repository
  uses an ignored project-local `.npm-cache` for repeatable commands.
- If the UI reports the API as unavailable, check that Uvicorn is listening on
  port 8000 and that `API_BASE_URL` is correct.
- A Docker named-pipe connection error means Docker Desktop is not running; it
  does not mean the Compose file is invalid.
- CORS tests use Starlette's current `httpx2` transport. Installing an unrelated
  legacy HTTPX version can reintroduce test-client warnings or incompatibility.
- A complete npm audit currently reports a Brace Expansion advisory through the
  ESLint development toolchain. Do not feed untrusted patterns into lint; track
  support for ESLint 10 in the Next.js React plugin before upgrading.

### Limitations

- The local machine had Node 26, so the pinned Node 24 target has not yet been
  exercised by CI.
- Compose configuration validates, but the PostgreSQL container was not started
  because Docker Desktop was unavailable.
- The production npm graph audits clean, but the development lint graph retains
  the documented Brace Expansion advisory until its upstream toolchain is
  compatible with the patched major release.
- Health contract types are maintained manually on both sides. Generated API
  types belong to the later contract phase.
- There are no product routes, persisted records, academic API calls, ranking,
  LLM behavior, authentication, or deployment yet.
- The visual layer is only a foundation preview; the reusable token system and
  responsive application shell belong to Phase 2.

### Next step

Create and approve `docs/plans/phase-02-design-system-and-responsive-shell.md`.
Then translate the Figma reference into design tokens and reusable primitives,
build the responsive navigation shell, and verify accessibility and reduced
motion without adding product behavior early.

---

## 2026-07-31 — Phase 02: Design system and responsive shell

### What was built

The Figma Make prototype was translated into a project-owned frontend system:

- semantic warm-neutral, teal, indigo, warning, and error tokens;
- locally bundled Manrope and Source Serif 4 variable fonts;
- an accessible brand header with desktop navigation, a mobile Sheet, current
  route semantics, and a skip link;
- reusable Button, Badge, Input, Textarea, Field, Separator, Skeleton, Sheet,
  status badge, layout, and data-state components;
- responsive shells for Profile, Discover, Mentors, Opportunities, and
  Applications;
- an internal `/design-system` gallery; and
- a redesigned landing page that preserves the real typed health boundary.

The route shells are intentionally honest. They describe their future product
surface but do not contain invented mentors, rankings, papers, opportunities,
or application records.

### Why it exists

Future product screens need a consistent visual and interaction language before
they accumulate feature-specific UI. This phase turns the best parts of the
prototype into reusable constraints, fixes its mobile and accessibility
problems, and gives Phase 3 stable routes and primitives to compose.

It also protects product credibility. Teal communicates verified evidence,
amber communicates unknown or incomplete information, and text labels always
accompany color. This keeps attractive presentation from turning uncertainty
into a false claim.

### Concepts introduced

- **Design token:** a named visual decision such as `brand-teal`, `surface`, or
  `border`. Components consume the role instead of repeating a raw hex value.
- **Semantic color:** color named by purpose rather than appearance. `unknown`
  explains meaning more reliably than `yellow`.
- **Component primitive:** a small owned building block with consistent states,
  focus behavior, and sizing. shadcn supplied source code, which was inspected
  and adapted rather than used as a remote UI runtime.
- **Client boundary:** only pathname-aware navigation and the interactive Sheet
  need browser JavaScript. Pages and most layout components remain Server
  Components.
- **Progressive disclosure:** desktop can show broad navigation while mobile
  moves it into a labelled drawer, preserving access without squeezing links.
- **Data state:** loading, empty, partial, unavailable, and error are distinct
  product outcomes. Treating them separately prevents a blank screen or a
  misleading success state.
- **Responsive invariant:** a condition that must remain true at every tested
  width, such as one main landmark, one page heading, and no horizontal scroll.
- **Self-hosted font asset:** the font files ship with the application build.
  The first build showed why this matters: `next/font/google` needed network
  access, while the local Fontsource packages build reproducibly offline.
- **Focus return:** after a modal navigation closes, keyboard focus returns to
  the control that opened it, so the user does not lose their place.

### Data flow

The visual shell introduces no new business-data flow. The only live request is
still the Phase 1 health boundary:

```text
browser request
  -> Next.js RootLayout
      -> skip link + responsive SiteHeader
      -> route Server Component
          -> landing page only: typed server-side health client
              -> FastAPI GET /api/v1/health
              -> available or unavailable HealthResult
          -> shared semantic component presentation
```

Navigation interaction is isolated:

```text
mobile menu button
  -> Radix Sheet client component
  -> labelled dialog + focus containment
  -> route Link
  -> Sheet closes and focus can return to the trigger
```

### Important files

- `apps/web/src/app/globals.css`: semantic tokens, Tailwind mappings, font
  roles, focus rules, reduced motion, and selection behavior.
- `apps/web/src/app/layout.tsx`: self-hosted fonts, skip link, metadata, and
  shared SiteHeader.
- `apps/web/src/components/navigation/site-header.tsx`: desktop and mobile
  navigation with `aria-current` and the Sheet client boundary.
- `apps/web/src/components/ui/`: repository-owned shadcn-derived primitives.
- `apps/web/src/components/states/data-state.tsx`: reusable loading, empty,
  error, partial, and unavailable presentation.
- `apps/web/src/components/layout/route-shell.tsx`: honest placeholder boundary
  reused by future product destinations.
- `apps/web/src/app/design-system/page.tsx`: running visual and state reference.
- `apps/web/src/app/page.tsx`: responsive editorial landing page with the live
  health status.
- `apps/web/src/config/navigation.ts`: typed navigation labels, destinations,
  descriptions, and icons.
- `docs/plans/phase-02-design-system-and-responsive-shell.md`: decisions,
  Figma audit, scope, acceptance criteria, and validation evidence.

### How to run and test it

Start the frontend from the repository root:

```powershell
npm.cmd run dev
```

Open `http://localhost:3000` and use `/design-system` to inspect the primitives.
To show the healthy full-stack state, start FastAPI in another terminal as
documented in `README.md`.

Run the frontend gates:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd audit --omit=dev --audit-level=high
```

The completed phase passed lint, strict TypeScript, 11 tests in five files, and
the production build. All seven routes were also measured at 360, 390, 768, and
1280 CSS pixels; all 28 combinations had no horizontal overflow and retained
exactly one `main` and one `h1`.

### Common errors and debugging

- If PowerShell blocks `npm.ps1`, use `npm.cmd`.
- If the build tries to contact `fonts.googleapis.com`, a Google font import has
  been reintroduced. Root layout should import the local Fontsource packages.
- If mobile content overflows, measure `document.documentElement.scrollWidth`
  against `innerWidth` and inspect long unbreakable specimens, grid items that
  lack `min-width: 0`, and fixed-width controls.
- If the mobile Sheet does not announce a useful name, keep `SheetTitle` and
  `SheetDescription`; visually hiding them is acceptable, removing them is not.
- If keyboard focus disappears after closing the Sheet, test focus return to
  the `Open navigation` trigger and avoid wrapping Radix close behavior in a
  component that drops event props or refs.
- If the health card says `API unavailable`, start FastAPI on port 8000. The
  unavailable state is still a valid and intentionally styled result.
- A Node engine warning means the local shell is using Node 26 rather than the
  repository's pinned Node 24 target.

### Limitations

- Route shells are layout boundaries, not working forms or data screens.
- The component gallery is internal documentation, not a public Storybook.
- Dark mode, localization, product motion, TanStack Query, React Hook Form,
  Zod, and Playwright remain out of scope until a phase needs them.
- No mentor, paper, opportunity, ranking, draft, or application fixture exists
  yet.
- The full npm audit retains the documented development-only Brace Expansion
  advisory in the lint graph; the production graph reports zero
  vulnerabilities.
- Browser layout checks were performed locally; automated cross-browser E2E
  coverage begins with the typed mock journey.

### Next step

Create and approve `docs/plans/phase-03-typed-mock-product-journey.md`. Define
the typed fixture contracts and complete recruiter-demo journey before adding
real academic APIs, persistence, ranking, or LLM behavior.

---

## 2026-07-31 — Phase 3: Typed mock product journey

### What was built

- A complete fictional placement-demo journey from student profile through
  discovery, researcher evidence, custom outreach, saved opportunities, and
  application tracking.
- Zod contracts for every demo entity and the complete browser state.
- A reducer-driven React context with schema-versioned, validated
  `sessionStorage` hydration and a global reset action.
- Three visibly fictional researcher records, five fictional papers, and three
  fictional opportunities. All source links use the reserved `example.org`
  domain.
- An honest discovery simulation with named stages and selectable complete,
  partial, empty, and error outcomes.
- A mobile list-to-detail mentor experience, selectable paper evidence, and an
  editable deterministic email draft with provenance links.
- Opportunity filtering/saving and an application tracker with explicit status
  changes, notes, follow-up dates, and event history.
- Unit tests for fixtures, state transitions, and draft grounding plus
  Playwright coverage for the recruiter journey, mobile detail flow, and all
  product routes at four responsive widths.

### Why it exists

Phase 2 proved the visual system. Phase 3 proves that the system can carry a
coherent product story a recruiter can operate and inspect before real APIs or
AI make the system expensive and harder to debug. It also freezes useful UI
contracts for Phase 4: the backend can replace the fixture adapter without
forcing a redesign.

The demo is intentionally complex in explainable ways: validated data,
deterministic state transitions, provenance, failure states, responsive
master-detail behavior, and automated critical-flow testing. It avoids
complexity that would be hard to defend, such as invented ranking scores,
agent labels, or fake live integrations.

### Concepts introduced

- **Runtime schema:** Zod checks data when it enters the application, while
  TypeScript checks how code uses that data during development.
- **Hydration boundary:** the UI waits for the browser snapshot to be validated
  before showing interactive forms, preventing saved data from overwriting fast
  user input.
- **Reducer:** a pure function maps the current state plus one named action to a
  new state. This makes transitions testable and avoids scattered mutations.
- **Versioned browser state:** the storage key and state schema carry a version,
  so later incompatible structures can be rejected or migrated deliberately.
- **Deterministic generation:** the outreach builder always produces content
  from selected, validated inputs. It can be tested without an LLM or network.
- **Evidence boundary:** an outreach draft can use the student profile, selected
  mentor, and selected papers—nothing else.
- **Master-detail interface:** desktop keeps candidates beside detail; mobile
  turns them into two focused screens with an explicit back action.
- **Honest partial failure:** available results remain visible while missing
  sources are named; the UI does not silently substitute invented data.
- **E2E test:** Playwright drives the built application like a user and verifies
  that independent components work as one journey.

### Data flow

```text
validated fictional fixtures
  -> createInitialDemoState()
  -> DemoProvider + demoReducer
      -> validate stored Phase 3 snapshot with Zod
      -> expose state and named actions to client features
          -> Profile saves allowed student facts
          -> Discover records query + explicit fixture outcome
          -> Mentors selects researcher + paper evidence
          -> deterministic draft builder
              -> editable draft + evidence URLs + mode/version
          -> Opportunities saves a source-linked fixture
          -> Applications records explicit status/history
      -> validate and persist the new tab-scoped snapshot
```

No Phase 3 route writes to FastAPI, PostgreSQL, an LLM, or an email provider.
The only existing backend request remains the landing-page health check.

### Important files

- `apps/web/src/features/demo/contracts.ts`: Zod schemas and inferred
  TypeScript types.
- `apps/web/src/features/demo/fixtures.ts`: canonical fictional entities and
  starting state.
- `apps/web/src/features/demo/demo-reducer.ts`: pure state transitions.
- `apps/web/src/features/demo/demo-store.tsx`: validated hydration, persistence,
  and React context.
- `apps/web/src/features/demo/draft-template.ts`: bounded deterministic email
  construction.
- `apps/web/src/features/profile/profile-experience.tsx`: validated profile
  form and allowed-fact explanation.
- `apps/web/src/features/discovery/discovery-experience.tsx`: staged fixture
  search and complete/partial/empty/error states.
- `apps/web/src/features/mentors/mentor-experience.tsx`: responsive evidence
  inspection, paper selection, editable draft, and tracking action.
- `apps/web/src/features/opportunities/opportunities-experience.tsx`: filters,
  source truth, unknown states, saving, and tracking.
- `apps/web/src/features/applications/applications-experience.tsx`: explicit
  tracker transitions and history.
- `apps/web/e2e/demo-journey.spec.ts`: critical journey, mobile, and responsive
  browser assertions.
- `apps/web/scripts/run-e2e.mjs`: reliable build-server-test cleanup on Windows.
- `docs/plans/phase-03-typed-mock-product-journey.md`: architecture, boundaries,
  risks, acceptance criteria, and verification record.

### How to run and test it

From the repository root:

```powershell
npm.cmd run dev
```

Open `http://localhost:3000` and select **Launch the product demo**. The product
routes work without the backend. To verify everything:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd audit --omit=dev --audit-level=high
```

The phase passes strict TypeScript, ESLint, 17 unit/component tests, the
production build, and four Playwright tests. The browser matrix covers five
product routes at 360, 390, 768, and 1280 pixels.

### Common errors and debugging

- If a form briefly shows defaults before saved data, the feature is rendering
  before `hydrated` becomes true. Keep the loading boundary outside the form so
  form hooks mount only after validation.
- If a stored snapshot is ignored, inspect the storage key
  `research-bridge.demo.phase-03.v1` and validate it against `demoStateSchema`.
  Resetting the demo replaces incompatible data safely.
- If a discovery test never finishes, inspect the named reducer actions and
  timer cleanup. Do not add fixed waits to tests; wait for the result heading.
- If an outreach draft lacks a profile edit, confirm the profile save completed
  and that persistence ran before a full reload.
- If a title-only paper produces a detailed claim, the deterministic template
  boundary has been violated. Title-only records may mention only title, year,
  and topic metadata cautiously.
- If Playwright leaves a Next process running on Windows, use
  `scripts/run-e2e.mjs`; it owns and closes the production server explicitly.
- If mobile content appears clipped, distinguish the intentionally scrollable
  workflow rail from page overflow by comparing document `scrollWidth` and
  `clientWidth`.
- A Node engine warning means the shell is using Node 26; use the pinned Node 24
  release for the supported environment.

### Limitations

- Every Phase 3 record is fictional and every product source URL is inert.
- `sessionStorage` is neither secure nor durable and is limited to one tab.
- Search progress is a local simulation, not OpenAlex or another academic API.
- Mentor ordering is explicitly not ranking; there are no numeric scores.
- The outreach builder is deterministic and local. It is not an LLM, does not
  discover email addresses, and cannot send messages.
- No authentication, user isolation, resume upload, database repository, or
  application API exists yet.
- The production npm dependency graph has zero reported vulnerabilities. The
  full development graph retains nine high-severity Brace Expansion advisories
  through ESLint plugins; npm only proposes a breaking ESLint 10 upgrade, so the
  repository keeps trusted lint globs and records the risk instead of forcing an
  incompatible upgrade.

### Next step

Phase 4 adds versioned FastAPI product contracts, structured errors, request
IDs, service interfaces, mock services, OpenAPI export, and a contract-checked
TypeScript client. The frontend fixture access will move behind that API without
changing the approved journey or introducing real academic retrieval yet.

---

## 2026-08-01 — Phase 04: Backend contracts

### What was built

The Phase 3 fictional journey now crosses a production-shaped HTTP boundary:

- FastAPI exposes versioned bootstrap, discovery, and outreach-draft routes;
- Pydantic validates strict camelCase request and response contracts;
- a `DemoService` protocol separates routes from the deterministic mock;
- fictional records and deterministic drafting moved from frontend runtime code
  to the backend fixture/service layer;
- one structured error envelope covers domain, validation, HTTP, and unexpected
  failures;
- request IDs, timing, and privacy-safe JSON logs make requests traceable;
- OpenAPI is exported, reviewed, and checked for drift;
- a TypeScript 6-compatible generator creates the Fetch SDK and types;
- Zod still validates network bytes because TypeScript disappears at runtime;
- TanStack Query owns bootstrap and mutation state; and
- Playwright starts both applications and tests real product requests.

### Why it exists

Phase 3 proved the interaction design, but all records and drafting behavior
lived in the browser bundle. That did not demonstrate backend layering, API
failure semantics, observability, or contract governance.

This phase creates that seam before database and provider complexity arrives. A
mock service behind the same interface is easy to test today and can later be
replaced by repository-backed and provider-backed implementations without
moving business logic into routes or rebuilding the UI.

### Concepts introduced

- **Transport versus business logic:** a route translates HTTP input/output;
  the service decides the deterministic outcome.
- **Protocol/interface:** `DemoService` describes behavior without requiring
  routes to know the concrete implementation class.
- **Dependency provider:** FastAPI resolves the service through one function,
  so tests and future environments can substitute implementations.
- **Application error:** an expected failure with a stable code, safe message,
  status, and optional field details.
- **Request ID:** an opaque identifier that connects a UI error, response
  header, and log record without logging private content.
- **Structured logging:** JSON fields such as path, status, duration, and
  request ID are machine-readable; profile and draft bodies are absent.
- **OpenAPI contract generation:** Pydantic and route definitions produce one
  reviewable API document, which generates frontend SDK types.
- **Compile-time versus runtime safety:** generated TypeScript prevents
  incorrect calls during development; Zod protects against malformed bytes.
- **Server state versus client state:** TanStack Query fetches/caches remote
  catalog state, while the reducer owns unsaved edits and workflow transitions.
- **Same-origin proxy:** browser code calls `/backend`; Next.js resolves the
  server-only API origin instead of exposing deployment configuration.

### Data flow

```text
product route mounts
  -> TanStack Query calls generated Fetch SDK
  -> Next.js /backend rewrite
  -> FastAPI request-ID middleware
  -> versioned route
  -> DemoService protocol
  -> MockDemoService + fictional backend fixtures
  -> Pydantic response validation
  -> generated TypeScript response type
  -> Zod runtime validation
  -> DemoProvider initializes reducer
  -> compatible sessionStorage edits are hydrated
  -> feature renders loading | error/retry | ready state

mentor + one/two papers + edited profile
  -> POST /api/v1/demo/outreach-drafts
  -> verify mentor/paper relationship
  -> deterministic evidence-bounded template
  -> provenance + uncertainty warnings
  -> editable local draft
  -> human may save/copy/track; no send action exists
```

### Important files

- `apps/api/app/schemas/demo.py`: product contracts and evidence constraints.
- `apps/api/app/services/demo.py`: service protocol.
- `apps/api/app/services/mock_demo.py`: deterministic discovery and drafting.
- `apps/api/app/fixtures/demo.py`: canonical fictional records.
- `apps/api/app/api/v1/routes/demo.py`: thin versioned transports.
- `apps/api/app/core/exception_handlers.py`: shared error mapping.
- `apps/api/app/core/middleware.py`: request identity and timing.
- `apps/api/openapi.json`: checked-in public contract.
- `apps/api/scripts/export_openapi.py`: deterministic export/drift command.
- `apps/web/scripts/generate-api.mjs`: generated-client and drift workflow.
- `apps/web/src/lib/api/generated/`: generated types, SDK, and Fetch transport;
  never hand-edit these files.
- `apps/web/src/lib/api/demo.ts`: runtime-validating API adapter.
- `apps/web/src/app/app-providers.tsx`: TanStack Query and demo-state roots.
- `apps/web/src/features/demo/demo-store.tsx`: bootstrap, compatibility checks,
  session hydration, retry, and local state.
- `apps/web/scripts/run-e2e.mjs`: owns FastAPI and Next.js test processes.
- `docs/plans/phase-04-backend-contracts.md`: decisions, risks, and evidence.

### How to run and test it

First create/sync the backend environment:

```powershell
Set-Location apps/api
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal from the repository root:

```powershell
npm.cmd run dev
```

The complete Phase 4 gates are:

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run python -m scripts.export_openapi --check

Set-Location ../web
npm.cmd run api:check
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
```

After an intentional backend contract change, export OpenAPI first, review it,
then generate and review the TypeScript SDK diff.

Verification completed with 11 backend tests, 17 frontend tests, and five
full-stack Playwright tests. The production build, strict typing, linting,
formatting, generated-contract checks, and manual 390px/desktop browser review
also pass. The intentional source-error scenario is fully handled and leaves no
browser console error.

### Common errors and debugging

- **Product routes show “Demo API unavailable”:** start FastAPI on port 8000,
  confirm `API_BASE_URL`, restart Next.js, and use the request ID to correlate
  the failure.
- **`openapi.json is stale`:** run `uv run python -m
  scripts.export_openapi`, inspect the diff, then regenerate the frontend SDK.
- **Generated client check fails:** never edit generated files. Run `npm.cmd run
  api:generate` after the backend export and review why the contract moved.
- **A saved session is discarded:** Phase 4 uses
  `research-bridge.demo.phase-04.v1` and verifies IDs against the API catalog.
- **`uv` cannot initialize its global cache in a restricted environment:** set
  `UV_CACHE_DIR` to a writable temporary directory for that command. This does
  not change the project virtual environment.
- **E2E cannot find Python:** run `uv sync --all-groups` in `apps/api`. The runner
  launches `.venv` Python directly so Windows cleanup owns the real process.
- **A UI error lacks a request ID:** expected server failures have one. A pure
  network failure has no server response and therefore cannot have one.

### Limitations

- The backend is stateless; profile edits, edited drafts, saves, and tracker
  history are still tab-scoped browser data.
- Every record and provider failure is fictional. OpenAlex is not contacted.
- Discovery outcomes are deterministic scenarios, not ranking or retrieval.
- Drafts use a deterministic fallback template, not an LLM, and cannot be sent.
- The bootstrap response bundles a small demo catalog; live records will require
  independently paginated endpoints.
- Authentication, PostgreSQL models, migrations, repositories, and ownership
  isolation have not been implemented.
- Production npm dependencies audit with zero known vulnerabilities. The pinned
  `@hey-api/openapi-ts` 0.97.0 generator has one moderate development-only
  template advisory and reads only trusted `apps/api/openapi.json`. Versions
  that fix it currently introduce a high-severity YAML parser advisory, so an
  upgrade must be retested instead of forced.

### Next step

Phase 5 — Database and profile introduces PostgreSQL persistence: SQLAlchemy 2
models, Alembic migrations, repositories, constraints, indexes, and durable
storage for the approved entities. It must preserve the Phase 4 route/service
boundary and must not introduce ranking or real academic retrieval early.

---

## 2026-08-01 — Phase 05: Database and durable profile

### What was built

Research Bridge now has its first durable product data path. SQLAlchemy 2 maps
an 18-table relational schema for ownership, student profiles, academic records,
provenance, opportunities, saves, outreach drafts, and application history.
Alembic owns a reviewed initial migration and downgrade. The profile route uses
repositories and one request transaction, while the existing demo bootstrap
composes the stored profile with the still-fictional catalog.

The profile form now saves through the generated TypeScript client and a
TanStack Query mutation. It displays pending, success, and safe failure states,
updates the shared server-state cache, and treats the database profile as more
authoritative than old browser-session state. The Playwright runner creates and
removes its own migrated SQLite database and never reuses a developer API.

### Why it exists

Phase 4 proved the HTTP boundary but every product edit disappeared with the
browser tab. Adding persistence before live academic APIs keeps the next phase
focused: OpenAlex normalization can store evidence in an already-tested schema
instead of mixing provider, migration, ownership, and frontend problems at
once.

The full schema is modelled now because Phase 5 owns relational design, but only
the profile aggregate has behavior. This avoids pretending that saved papers,
applications, or generated drafts are durable before their roadmap phases.

### Concepts introduced

- **ORM model:** a typed Python class mapped to a relational table; SQLAlchemy
  still produces explicit SQL and does not replace database constraints.
- **Migration:** an ordered, reviewable schema change. Alembic upgrades an
  existing database; application startup never silently creates tables.
- **Aggregate:** a record and the children changed with it. A profile save
  replaces its ordered interests, skills, and project in one transaction.
- **Repository:** the database access boundary. Services depend on repository
  protocols instead of writing SQL from routes.
- **Unit of work/transaction:** all statements in one request either commit
  together or roll back together.
- **Ownership anchor:** `account_owners` partitions private rows, but it is not
  authentication. The server resolves the demo owner; the browser cannot choose
  an owner ID.
- **Natural/provider ID versus internal ID:** application rows use UUIDs while
  DOI, OpenAlex, Semantic Scholar, ORCID, ROR, and source IDs remain explicit.
- **Provenance:** source URL, record ID, verification time, fields, and optional
  content hash record where an academic fact came from.
- **Schema drift:** a mismatch between ORM metadata and migrated tables.
  `alembic check` detects it before deployment.
- **Server state:** the saved profile belongs to the API/query cache. Temporary
  workflow choices remain reducer/session state until their own phases.

### Data flow

```text
Profile form
  -> React Hook Form + Zod validation
  -> TanStack Query mutation
  -> generated PUT /api/v1/demo/profile client
  -> FastAPI request-ID/error boundary
  -> profile route
  -> ProfileService
  -> owner + profile repositories
  -> request-scoped AsyncSession transaction
  -> PostgreSQL
  -> validated StudentProfile response
  -> query cache + reducer update

Later page load
  -> GET /api/v1/demo/bootstrap
  -> MockDemoService asks ProfileService for the stored profile
  -> stored profile overrides stale sessionStorage profile data
  -> fictional mentors/opportunities remain deterministic fixtures
```

### Important files

- `apps/api/app/db/base.py`: declarative base, UUIDs, timestamps, and stable
  constraint naming.
- `apps/api/app/db/models/`: ownership, profile, academic, provenance, and
  workflow mappings.
- `apps/api/alembic/`: async migration environment and reversible initial
  schema.
- `apps/api/app/db/session.py`: async engine and session factory.
- `apps/api/app/dependencies/database.py`: request transaction commit/rollback.
- `apps/api/app/repositories/owners.py`: server-owned demo account anchor.
- `apps/api/app/repositories/profiles.py`: eager aggregate read and atomic
  upsert/child replacement.
- `apps/api/app/services/profile.py`: persistence use case and ORM-to-contract
  mapping.
- `apps/api/app/api/v1/routes/profile.py`: thin GET/PUT transport.
- `apps/web/src/features/profile/profile-experience.tsx`: accessible durable
  save interaction.
- `apps/web/src/features/demo/demo-store.tsx`: server-authoritative profile
  hydration.
- `apps/web/scripts/run-e2e.mjs`: isolated migrated full-stack test harness.
- `docs/plans/phase-05-database-and-profile.md`: scope, model, risks, and
  verification decisions.

### How to run and test it

Start the database from the repository root, then migrate from `apps/api`:

```powershell
docker compose up -d db
Set-Location apps/api
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Run the frontend from a second root terminal:

```powershell
npm.cmd run dev
```

Phase 5 verification completed with 18 backend tests, 18 frontend tests, and
five full-stack Playwright tests. The browser suite proved that a profile
survives cleared session storage and reload. A disposable PostgreSQL 17 database
also passed upgrade, head check, zero-drift check, profile save/bootstrap reload,
and downgrade.

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run alembic upgrade head --sql
uv run python -m scripts.export_openapi --check

Set-Location ../..
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
```

### Common errors and debugging

- **`relation student_profiles does not exist`:** run `uv run alembic upgrade
  head` against the same `DATABASE_URL` used by FastAPI.
- **Health works but profile loading fails:** health measures the process, not
  database readiness. Check PostgreSQL, `DATABASE_URL`, migration head, and the
  response request ID.
- **Password authentication fails unexpectedly:** verify which PostgreSQL
  service owns the configured host port. Another local service on this machine
  occupied 5432; the live smoke test used Docker on 55432.
- **Psycopg reports `ProactorEventLoop`:** Phase 5 intentionally uses
  `postgresql+asyncpg`, which is supported by SQLAlchemy's async engine and
  Uvicorn's default Windows loop.
- **`alembic check` reports new operations:** the ORM and migration disagree.
  Review the intended model change and create a migration; do not silence the
  drift check.
- **A second profile save hits an ordered-child uniqueness error:** old children
  must be flushed as deletes before inserting replacements with reused
  positions. The repository implements and tests this ordering.
- **`uv` cannot initialize its global cache:** set `UV_CACHE_DIR=.uv-cache`; the
  directory is already ignored and does not change `.venv` activation.

### Limitations

- The ownership anchor does not authenticate or authorize anyone. Only
  fictional profile data is appropriate until Phase 10.
- Only the profile is durable. Draft edits, opportunity saves, and application
  tracking still use tab-scoped session storage.
- Academic tables are empty and have no ingestion repositories yet; OpenAlex
  begins in Phase 6.
- Ranking, embeddings, pgvector usage, OpenSearch, Redis, background workers,
  LangGraph, LLM calls, and email sending remain absent.
- The fixed demo owner is suitable for a local portfolio demo, not a multi-user
  deployment.
- Concurrent first writes for the same fixed demo owner are constrained by the
  database but are not yet retried as an idempotent operation.
- Polymorphic provenance keeps one shared entity ID without a physical foreign
  key; later repositories must validate the target kind and ID together.

### Next step

Phase 6 integrates OpenAlex behind a typed async client with explicit timeouts,
bounded retries, rate-limit and partial-failure handling, normalization,
deduplication, and provenance writes. It will not add ranking yet: retrieved
evidence must be correct and measurable before candidate ordering becomes its
own Phase 7 concern.

---

## 2026-08-01 — Phase 06: OpenAlex discovery and normalization

### What was built

Research Bridge now has its first live academic-data path. A student can search
for papers with a focused topic, a DOI, or an OpenAlex Work ID. FastAPI
classifies the query, retrieves only the required OpenAlex fields through one
application-scoped async client, validates provider records, reconstructs
abstracts, normalizes academic identities, removes duplicate works, and stores
the surviving evidence with provenance.

The academic persistence model now preserves OpenAlex institution IDs, paper
type/language/retraction state, OpenAlex topic IDs and provider scores, and all
institutions attached to each paper-specific authorship. The frontend presents
the results in a responsive evidence workspace with source links, visible
unknowns, title-only warnings, partial/error/empty/loading states, and a clear
“OpenAlex provider order — not Research Bridge ranked” label. The deterministic
recruiter demo remains available in an adjacent tab.

### Why it exists

Professor matching is only defensible when its supporting papers are reliable.
Phase 6 therefore builds the evidence boundary before deriving mentors or
calculating relevance. This separation gives Phase 7 clean, persisted inputs
and prevents a recruiter demo from implying that an LLM or an unexplained score
selected a professor.

Keeping live discovery beside a deterministic demo solves two different needs:
live mode proves real API integration and provenance, while demo mode stays
reliable during interviews even when OpenAlex is unavailable or an allowance
is exhausted.

### Concepts introduced

- **Provider DTO versus public schema:** provider DTOs tolerate the external
  OpenAlex shape. Public schemas expose only Research Bridge’s reviewed,
  normalized contract. This prevents provider changes from leaking directly
  into the UI.
- **Dependency inversion:** the discovery service depends on an academic
  provider protocol, not the concrete OpenAlex client. Tests replace that
  boundary with fixtures without changing business logic.
- **Application lifespan:** one async HTTP client and connection pool are
  created for the FastAPI process and closed at shutdown. Creating a new client
  for every request would discard pooling and increase latency.
- **Timeout categories:** connect bounds opening a socket, read bounds waiting
  for response bytes, write bounds sending request bytes, and pool bounds
  waiting for a reusable connection.
- **Retry budget:** an idempotent GET may retry only a small set of transient
  failures. Capped exponential backoff creates increasing pauses without
  retrying forever. Daily allowance failures are surfaced rather than amplified.
- **Query classification:** text, DOI, and OpenAlex Work ID searches use known
  request templates. User input never chooses the provider host, which is an
  important SSRF defense.
- **Inverted-index reconstruction:** OpenAlex can supply an abstract as words
  mapped to positions. Deterministic code validates positions, detects
  conflicts, orders tokens, and applies size bounds before producing text.
- **Conservative identity resolution:** canonical OpenAlex IDs, DOI, ORCID, and
  ROR are preferred. Title/year fallback is used only when both provider IDs
  are absent. Unknown identity remains unknown instead of being guessed.
- **Paper-specific affiliation:** an author may have multiple institutions on
  one historical paper. The affiliation belongs to the
  paper-author-institution relationship, not an assumed current employer.
- **Idempotent upsert:** replaying the same provider records updates their
  aggregate instead of creating duplicates. Database constraints and one
  transaction protect the invariant.
- **Provenance hash:** a stable SHA-256 hash represents the normalized fields
  supplied by a source. It supports later change detection without treating the
  hash as evidence itself.
- **Cache-aside:** the service reads a bounded TTL cache before calling the
  provider and fills it after validation. Only normalized provider values are
  cached; persistence still runs on a hit. The current cache is process-local,
  not shared infrastructure.
- **Partial success:** malformed or retracted individual records can be skipped
  while valid papers remain visible with structured warnings. A total provider
  failure uses the shared error envelope and request ID.
- **Provider order versus ranking:** OpenAlex’s response order is displayed as
  received. A provider topic score is metadata about a topic assignment; it is
  not a student-professor match score.

### Data flow

```text
Live discovery form
  -> React Hook Form + Zod validation
  -> TanStack Query mutation + abort signal
  -> generated POST /api/v1/discovery/papers client
  -> FastAPI route + request transaction
  -> DiscoveryService
      -> classify text / DOI / OpenAlex Work ID
      -> bounded cache lookup
      -> OpenAlex provider
          -> application-scoped async HTTPX2 client
          -> timeout + retry + rate-limit boundary
          -> provider DTO validation
      -> deterministic normalization + deduplication
      -> academic repository upsert
          -> papers + authors + institutions
          -> ordered authorships + paper-specific affiliations
          -> topics + provenance
      -> validated public response
  -> responsive evidence list with source and uncertainty

Repeated identical query
  -> normalized cache key includes query kind, limit, and normalizer version
  -> provider call skipped while entry is fresh
  -> persistence still runs idempotently
  -> UI shows “Provider cache hit”
```

### Important files

- `apps/api/app/clients/openalex.py`: encoded OpenAlex requests, explicit
  timeouts, bounded retries, rate-limit parsing, and secret-safe failures.
- `apps/api/app/providers/base.py`: provider protocol and normalized academic
  value objects.
- `apps/api/app/providers/openalex/models.py`: tolerant raw provider DTOs.
- `apps/api/app/providers/openalex/normalizer.py`: Unicode/identifier cleanup,
  abstract reconstruction, deduplication, warnings, and content hashes.
- `apps/api/app/services/search_cache.py`: bounded async-safe TTL/LRU cache.
- `apps/api/app/services/discovery.py`: cache-aside orchestration and public
  outcome mapping.
- `apps/api/app/repositories/academic.py`: transactional, idempotent catalog and
  provenance persistence.
- `apps/api/alembic/versions/20260801_0002_openalex_catalog.py`: additive and
  reversible Phase 6 schema change.
- `apps/api/app/api/v1/routes/discovery.py`: thin live discovery transport.
- `apps/web/src/features/discovery/live-paper-discovery.tsx`: responsive live
  form and complete/partial/empty/error/loading evidence states.
- `apps/web/src/lib/api/discovery.ts`: generated-client adapter plus runtime Zod
  response validation.
- `apps/web/scripts/run-e2e.mjs`: isolated migrated database and owned loopback
  OpenAlex fixture server.
- `docs/plans/phase-06-openalex-discovery-and-normalization.md`: scope,
  architecture decisions, risks, and acceptance evidence.

### How to run and test it

Configure and migrate the backend:

```powershell
Copy-Item apps/api/.env.example apps/api/.env
# Optional but recommended: set OPENALEX_API_KEY in apps/api/.env

docker compose up -d db
Set-Location apps/api
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Run the frontend from a second root terminal:

```powershell
npm.cmd run dev
```

Open `http://localhost:3000/discover`, keep **Live OpenAlex papers** selected,
and search a focused topic. The recruiter journey remains under **Recruiter
demo**.

Phase 6 completion passed 48 backend tests, 22 frontend tests, and seven isolated
Playwright tests. Ruff, Ruff formatting, mypy, OpenAPI drift, generated-client
drift, lint, typecheck, production build, production dependency audit, and
Compose validation passed. A disposable PostgreSQL 17 database passed upgrade,
zero-drift, ingestion, fresh-process idempotency, downgrade, and re-upgrade.
Manual browser QA passed at desktop and 390px with no document overflow or
console warning/error.

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run python -m scripts.export_openapi --check

Set-Location ../..
npm.cmd run lint
npm.cmd run typecheck
npm.cmd --workspace @research-bridge/web run api:check
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
```

### Common errors and debugging

- **`academic_source_rate_limited`:** the provider rejected the allowance.
  Wait for the displayed retry window or configure a server-only OpenAlex key.
  Do not add an automatic retry loop around allowance exhaustion.
- **`academic_source_unavailable`:** check internet access, the request ID, and
  FastAPI logs. The public error deliberately omits the upstream URL when it
  could contain a key.
- **OpenAlex works anonymously but fails after adding a key:** restart FastAPI
  after editing `.env` and ensure the value has no surrounding placeholder
  characters. Never place it in frontend environment files.
- **`openalex_base_url` validation fails:** normal development accepts only the
  official HTTPS origin. Loopback HTTP is deliberately limited to test/E2E.
- **Search works but persistence reports a missing column/table:** run `uv run
  alembic upgrade head` against the same `DATABASE_URL` FastAPI uses.
- **A title-only result appears:** this is expected when no valid abstract was
  supplied. Do not infer methods, findings, or fit from the title.
- **A repeated query still calls OpenAlex:** cache keys include query type and
  limit, entries expire, and every FastAPI process owns a separate cache.
- **`alembic check` reports operations:** ORM metadata and the applied migration
  disagree. Create/review a migration instead of letting startup mutate schema.
- **The live browser test unexpectedly spends provider allowance:** normal
  automated E2E must use its loopback fixture. Check that the runner sets the
  test-only loopback origin before starting the API.

### Limitations

- Phase 6 discovers papers, not professors. Mentor derivation and transparent
  student relevance begin in Phase 7.
- Only OpenAlex is live. Semantic Scholar, Crossref, ORCID, arXiv, and
  controlled extraction remain deferred.
- The cache is bounded but process-local; it has no cross-process invalidation
  or durable search history.
- Topic scores come from OpenAlex and are not Research Bridge ranking scores.
- Provider DTO tolerance reduces breakage but cannot guarantee that OpenAlex
  will never make an incompatible contract change.
- A manual request to the real provider was not made during completion because
  no personal OpenAlex key was configured. Deterministic client tests, the
  owned provider stub, and current official documentation covered the boundary
  without consuming external allowance.
- Authentication, private-user isolation, ranking, LLM explanations, outreach
  generation, and email sending remain absent.

### Next step

Phase 7 derives mentor candidates from persisted paper authors and implements a
transparent placement-release relevance heuristic with feature contributions,
evidence completeness, uncertainty, and evaluation measurements. It must keep
provider metadata separate from Research Bridge relevance and must not claim
research-grade ranking quality.

---

## 2026-08-01 — Phase 07: Basic relevance and evidence

### What was built

Research Bridge can now turn live OpenAlex paper results into reviewable
researcher candidates. `POST /api/v1/discovery/mentors` reuses the existing
paper-discovery service and saved-profile reader, groups repeated authors by
their stable internal author ID, retains every supporting paper, and applies
the versioned `placement-relevance-v1` policy.

The public response includes an evidence band, evidence confidence, five
individual feature contributions, matched terms, supporting paper IDs,
paper-specific affiliations, source URLs, verification time, request quality
metrics, and separate retrieval/heuristic timing. It does not expose the
internal total as a compatibility score. Academic title, current institution,
contact information, and availability stay unknown.

The `/mentors` page now opens in live mode with a teal-and-indigo responsive
master-detail workspace. It has accessible live/demo tabs, validated query
form, loading/empty/partial/error/complete states, evidence bars, source links,
historical-affiliation labels, mobile back/focus behavior, and query prefill
from `/discover`. The existing fictional mentor and outreach journey remains a
separate recruiter-demo mode.

An offline evaluator and checked-in baseline measure duplicate collapse,
candidate retrieval success, mean evidence coverage, unsupported positive
contributions, and pure-policy latency against tiny deterministic fixtures. No
new dependency was required.

### Why it exists

Paper retrieval alone leaves a student to inspect every author manually. A
review order helps, but an opaque “AI fit score” would be difficult to defend
and easy to overstate in an interview. This phase adds only the minimum
deterministic prioritization needed for the placement release while keeping
advanced ranking research deferred.

The important product boundary is that an author of a relevant paper is only a
researcher candidate. OpenAlex authorship does not prove that the person is a
professor, currently works at a historical affiliation, accepts students, or
has a reachable email address. Showing those facts as unknown is a correctness
feature, not missing polish.

### Concepts introduced

- **Candidate generation versus ranking:** candidate generation decides who is
  eligible—the authors of validated supporting papers. The Phase 7 policy then
  creates a review order. It is not a learned ranking model or a prediction of
  supervision suitability.
- **Entity grouping:** the same author can appear on several papers. Grouping by
  the conservative internal UUID collapses repeated appearances while keeping
  distinct UUIDs separate even when names match.
- **Historical relationship:** an affiliation belongs to one
  paper-author-institution relationship. Copying it into `currentInstitution`
  would turn historical evidence into an unsupported current-employment claim.
- **Feature normalization:** each observed signal is converted into the range
  zero to one so unlike quantities can be combined predictably.
- **Weight and contribution:** a weight states policy importance. A
  contribution is `normalized value × weight`. We expose these parts so the
  order can be reconstructed and challenged.
- **Evidence band:** the internal contribution total maps to strong, promising,
  or exploratory. A band avoids false numeric precision while still helping a
  student decide what to inspect first.
- **Deterministic tie-breaking:** equal totals fall back to supporting-paper
  count, Unicode-normalized display name, and UUID. The same inputs, weights,
  and evaluation year therefore produce the same order.
- **Lexical overlap:** the tokenizer uses Unicode NFKC normalization, case
  folding, token extraction, and a small stopword set. Overlap is observable
  text evidence, not proof of semantic expertise; embeddings and reranking
  remain Phase 14 research.
- **Evidence completeness versus confidence:** completeness measures available
  publication metadata. Confidence summarizes the stability and depth of that
  evidence. Neither claims that the researcher is a good supervisor.
- **Claim-support audit:** every positive policy contribution must carry at
  least one supporting paper ID. The unsupported-claim rate makes this
  structural invariant measurable.
- **Request versus offline metrics:** a live response describes one request.
  The evaluator repeats pure fixture derivation to establish a reproducible
  baseline. Neither replaces labelled relevance evaluation.
- **Dependency inversion:** `MentorDiscoveryService` depends on
  `PaperDiscoveryReader` and `ProfileReader`, so it composes tested services
  instead of duplicating provider or persistence code.
- **Live versus demo state:** live results are TanStack Query server state. The
  fictional outreach catalog and selections remain isolated session/demo state;
  the two contracts are never cast into each other.

### Data flow

```text
Live mentor form
  -> React Hook Form + Zod
  -> generated POST /api/v1/discovery/mentors client
  -> FastAPI mentor route
  -> MentorDiscoveryService
      -> ProfileReader
          -> saved fictional profile or safe fixture fallback
      -> PaperDiscoveryReader
          -> OpenAlex cache/provider/normalizer/repository
      -> pure CandidateDeriver
          -> group author UUIDs across papers
          -> tokenize query and profile evidence
          -> calculate 5 normalized feature values
          -> multiply by validated policy weights
          -> assign evidence band and confidence
          -> attach evidence IDs and audit claims
          -> deterministic tie-break
  -> strict response + generated TypeScript + runtime Zod
  -> responsive candidate list and evidence detail

Live paper result
  -> “Find researchers”
  -> /mentors?query=<encoded normalized query>
  -> prefilled form; user explicitly starts derivation
```

### Important files

- `apps/api/app/relevance/mentor.py`: pure tokenizer, grouping, five features,
  banding, confidence, tie-breaking, and request quality metrics.
- `apps/api/app/services/mentor_discovery.py`: profile/paper composition,
  timing, and public evidence mapping.
- `apps/api/app/schemas/mentor_discovery.py`: strict request, policy,
  candidate, supporting-paper, quality, and timing contracts.
- `apps/api/app/dependencies/mentor_discovery.py`: request-scoped service
  composition and injected evaluation year/weights.
- `apps/api/scripts/evaluate_mentor_relevance.py`: deterministic offline
  baseline generator and drift check.
- `apps/api/evaluation/mentor-relevance-v1.json`: tiny reviewed evaluation
  fixture.
- `apps/api/reports/phase-07-relevance-baseline.json`: checked-in honest
  baseline and limitations.
- `apps/web/src/features/mentors/live-mentor-discovery.tsx`: live responsive
  form, states, candidate master-detail, contributions, and evidence.
- `apps/web/src/features/mentors/mentor-mode-experience.tsx`: accessible live
  and recruiter-demo mode boundary.
- `apps/web/src/lib/api/mentors.ts`: generated-client adapter with runtime Zod
  validation.
- `docs/plans/phase-07-basic-relevance-and-evidence.md`: approved scope,
  formulas, risks, and completion evidence.

### How to run and test it

Start PostgreSQL, migrate, and run FastAPI:

```powershell
docker compose --env-file .env up -d db
Set-Location apps/api
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Run Next.js from a second root terminal:

```powershell
npm.cmd run dev
```

Open `http://localhost:3000/discover`, retrieve papers, and choose **Find
researchers**, or open `/mentors` directly. The form does not call OpenAlex
until the user submits it.

Phase 7 completion passed 56 backend tests, 26 frontend tests, and eight
isolated Playwright tests. Ruff, formatting, strict mypy, OpenAPI drift,
generated-client drift, ESLint, strict TypeScript, production build, evaluator
drift, responsive overflow, reduced motion, and manual desktop/390px browser QA
passed. A uniquely named disposable PostgreSQL database and role also passed
migration head, zero-drift, and two fresh-process endpoint runs before both
temporary targets and the test container were removed.

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run python -m scripts.export_openapi --check
uv run python -m scripts.evaluate_mentor_relevance --check

Set-Location ../..
npm.cmd run lint
npm.cmd run typecheck
npm.cmd --workspace @research-bridge/web run api:check
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
```

### Common errors and debugging

- **No candidates appear:** confirm the paper query returns validated works with
  authors. Broaden a narrow topic or validate the DOI/OpenAlex ID first.
- **`mentor relevance weights must total one`:** all five `MENTOR_*_WEIGHT`
  values are bounded and must add to exactly 1.0. Restart FastAPI after editing
  `.env`.
- **A researcher has no institution or title:** inspect the paper-specific
  affiliations. Current employment and title intentionally remain unknown.
- **A repeated author appears twice:** inspect OpenAlex/internal author IDs. The
  policy groups stable IDs, not display names, because name-only merging can
  combine different people.
- **A result seems lexically weak:** inspect its matched terms, feature values,
  paper depth, and completeness. Phase 7 deliberately has no synonyms,
  stemming, embeddings, or semantic reranker.
- **The checked baseline is stale:** run `uv run python -m
  scripts.evaluate_mentor_relevance`, review the stable metric change, then run
  it again with `--check`. Timing is machine-local and excluded from stable
  drift comparison.
- **`uv` cannot initialize its global cache:** use the existing `.venv`
  executables or set `UV_CACHE_DIR=.uv-cache`; the workspace cache is ignored.

### Limitations

- Only OpenAlex is live; current-role verification through ORCID/ROR or an
  official university directory is future work.
- The server uses the saved fictional profile or a fictional fallback until
  authentication and private-user isolation exist.
- Lexical matching can miss synonyms and cannot judge methodological fit.
- Default weights are policy choices, not trained or tuned parameters.
- The fixture baseline is too small and unlabelled for Recall@5/10, MRR,
  nDCG@10, or a claim of general search quality.
- A paper author is not automatically a professor or available supervisor.
- Live evidence cannot create outreach yet. The existing draft flow remains a
  fictional deterministic demo until Phase 8 safely connects real evidence.
- No email is sent automatically, and no contact address is inferred.

### Next step

Phase 8 adds evidence-grounded outreach for live candidates. The user must
select one researcher and specific supporting papers, review the generated
draft, and approve any external use. Prompts will be versioned, outputs will be
structurally validated, claims will map to verified profile/paper evidence, and
a deterministic fallback will remain available. The product still will not
mass-send or automatically send email.

## 2026-08-01 — Phase 08: Evidence-grounded outreach

### What was built

The live researcher journey now continues from evidence inspection into a safe
outreach workspace. A student selects one researcher and one or two supporting
papers, chooses either the best available generator or the deterministic
template, and creates a persisted draft. The result exposes the exact profile
facts and papers used, a claim-to-evidence map, uncertainty warnings,
generation provenance, the current version, and revision history.

The optional generator is a narrow OpenAI Responses API adapter. It requests a
strict JSON structure with the versioned prompt `outreach-grounded.v1`, uses low
reasoning and bounded output, disables provider-side storage, and never receives
an email address. If the key is absent or the provider times out, refuses,
returns invalid JSON, cites unknown evidence, or produces unsafe prose, the
server creates the deterministic `outreach-template.v1` draft instead.

Draft editing is durable. Each successful save updates the convenient latest
snapshot and appends an immutable numbered revision in the same transaction. An
expected-version field prevents one browser view from silently overwriting a
newer save. Editing changes the evidence-map status to
`manual-edit-needs-review`, clears the browser review acknowledgement, and
requires another explicit review before copy is enabled. Research Bridge AI has
no send button, SMTP client, Gmail/Outlook connector, or inferred recipient
address.

### Why it exists

A generic cold email is easy to produce and easy for a recruiter to dismiss.
The engineering value is in proving why each customized statement is allowed.
This phase treats generation as an untrusted composition step inside a larger
deterministic workflow: trusted code selects evidence, validates references,
applies uncertainty rules, chooses fallback behavior, persists versions, and
requires human approval.

That boundary also makes the feature useful without paid model access. The
deterministic template is a real supported path rather than an error message,
so development, testing, recruiter demos, and provider outages all retain the
same evidence and persistence guarantees.

### Concepts introduced

- **Server-reconstructed evidence:** the browser sends IDs and the original
  query, not factual prose. The server reruns discovery and rejects a researcher
  or paper that is not in that verified result.
- **Structured generation:** the model may return only a small typed
  composition. Pydantic validation rejects missing, extra, or malformed fields
  before any prose becomes a draft.
- **Prompt versioning:** `outreach-grounded.v1` identifies the exact behavioral
  contract used for model-assisted composition. Template and prompt versions are
  stored separately because deterministic and model paths evolve differently.
- **Grounding audit:** every generated paragraph must cite allowlisted profile
  fact keys or selected paper UUIDs. Unknown references and unsupported claims
  fail closed to the deterministic template.
- **Title-only evidence:** a paper title proves that the title exists; it does
  not prove a method, result, or conclusion. Model prose based only on a title is
  replaced with a conservative deterministic sentence.
- **Graceful degradation:** a provider failure changes generation provenance,
  not the usefulness of the request. Safe fallback reasons are public, while
  keys and raw provider details are not logged or persisted.
- **Optimistic concurrency:** `expectedVersion` says which version the user
  edited. A mismatch returns 409 instead of overwriting another saved revision.
- **Snapshot plus revision log:** the latest draft row makes normal reads simple;
  immutable revision rows preserve history for audit and interview explanation.
- **Human-in-the-loop gate:** review is an explicit user action tied to the
  current saved subject/body. Copying is deliberately different from sending.
- **Runtime contract checking:** generated TypeScript types help at compile
  time, while Zod verifies that a live API response—including UTC timestamps—
  matches the browser's assumptions.
- **Structural evaluation:** the Phase 8 evaluator measures rejection of invalid
  evidence references and unsupported assertions. It does not pretend to
  measure email response probability or writing quality.

### Data flow

```text
Live mentor detail
  -> user selects 1 researcher + 1–2 supporting paper IDs
  -> POST /api/v1/outreach/drafts
  -> OutreachService reruns bounded mentor discovery
      -> OpenAlex evidence + normalized database catalog
      -> saved fictional profile or safe fictional fallback
  -> build server-owned evidence package
  -> deterministic request/no key?
      -> outreach-template.v1
     otherwise
      -> Responses API + outreach-grounded.v1 strict JSON
      -> Pydantic structure check
      -> evidence-reference and prose grounding checks
      -> unsafe output? deterministic fallback
  -> one database transaction
      -> latest outreach_drafts snapshot
      -> selected draft_papers links
      -> outreach_draft_revisions version 1
  -> strict API response + generated TypeScript + Zod
  -> editor + provenance + claim-to-evidence inspector

Edited subject/body + expectedVersion
  -> PUT /api/v1/outreach/drafts/{id}
  -> owner scope + row/version check
  -> update latest snapshot + append immutable revision
  -> manual-edit-needs-review
  -> user reviews current saved text
  -> copy to clipboard only; no send transport
```

### Important files

- `apps/api/app/outreach/drafting.py`: evidence package, version constants,
  deterministic template, provider-output grounding, title-only policy, and
  safe fallback domain errors.
- `apps/api/app/providers/openai_outreach.py`: bounded Responses API adapter,
  strict JSON Schema request, retries, refusal parsing, and secret-safe errors.
- `apps/api/app/services/outreach.py`: selection revalidation, provider/fallback
  orchestration, persistence mapping, and public UTC normalization.
- `apps/api/app/repositories/outreach.py`: owner-scoped create/read/update,
  transactional revisions, row locking, and version conflicts.
- `apps/api/app/schemas/outreach.py`: strict create, update, evidence,
  provenance, revision, and response contracts.
- `apps/api/alembic/versions/20260801_0003_outreach_revisions.py`: schema upgrade
  for grounding metadata and immutable revisions.
- `apps/api/scripts/evaluate_outreach_grounding.py` and
  `apps/api/reports/phase-08-outreach-grounding-baseline.json`: reproducible
  structural grounding baseline and honest limitations.
- `apps/web/src/features/outreach/live-outreach-workspace.tsx`: paper selection,
  mode choice, async states, editor, evidence inspector, save/review/copy gates.
- `apps/web/src/features/outreach/contracts.ts`: runtime Zod boundary for the
  live response.
- `apps/web/src/lib/api/outreach.ts`: checked adapter around the generated API
  client.
- `docs/plans/phase-08-evidence-grounded-outreach.md`: decisions, threat
  boundaries, contracts, and completion evidence.

### How to run and test it

Apply the new migration and start the API:

```powershell
docker compose --env-file .env up -d db
Set-Location apps/api
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

`OPENAI_API_KEY` is optional. Leave it unset to exercise the deterministic
fallback. To test model-assisted composition manually, put the key only in
`apps/api/.env`, keep the official base URL, and restart FastAPI. Then start the
frontend from the repository root:

```powershell
npm.cmd run dev
```

Open `/discover`, retrieve live paper evidence, choose **Find researchers**,
run the researcher search, select paper evidence, and build a draft. Inspect the
generation badges and evidence map, edit the subject or body, save version 2,
acknowledge review, and copy it.

The Phase 8 automated gates are:

```powershell
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run python -m scripts.export_openapi --check
uv run python -m scripts.evaluate_mentor_relevance --check
uv run python -m scripts.evaluate_outreach_grounding --check

Set-Location ../..
npm.cmd run lint
npm.cmd run typecheck
npm.cmd --workspace @research-bridge/web run api:check
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
```

The isolated Playwright runner migrates a temporary SQLite database, starts a
loopback OpenAlex fixture, and never calls OpenAI. This keeps the full browser
journey reproducible and free of API cost.

### Common errors and debugging

- **Deterministic fallback appears unexpectedly:** inspect `fallbackReason` in
  the evidence panel. `provider-not-configured` means the optional key is absent;
  refusal, unavailable, invalid-output, and grounding failures are separate.
- **`422 outreach_mentor_not_found` or `outreach_paper_not_found`:** the selected
  ID was not present when the server reconstructed the bounded discovery result.
  Run the search again and select from the current candidate evidence.
- **`409 draft_version_conflict`:** another save already advanced the version.
  Reload the latest draft before applying the edit again.
- **The review checkbox is disabled:** save the current edits first. Review is
  intentionally tied to the latest persisted subject and body.
- **Clipboard copy fails:** browser permissions may deny programmatic clipboard
  access. The draft remains editable so it can be selected and copied manually.
- **A timestamp fails the browser contract in SQLite:** stored SQLite datetimes
  can be naive. All outreach persistence timestamps must pass through the UTC
  response normalizer; PostgreSQL already returns timezone-aware values.
- **Tables or columns are missing:** run `uv run alembic upgrade head` and check
  the database URL used by the API process.
- **`uv` cache initialization fails on Windows:** use the existing
  `.venv\Scripts\python.exe` for a focused check or set a workspace-local
  `UV_CACHE_DIR`.

### Limitations

- Authentication is not implemented. A server-only demo owner partitions
  records, and the stored profile is intentionally fictional.
- Only OpenAlex publication evidence is live. Recipient title, current
  institution, contact address, availability, funding, and open positions remain
  unknown.
- The grounding audit is a conservative structural and phrase-based guard, not
  a complete semantic fact checker. Representative human evaluation is still
  required before claiming prose quality.
- The checked evaluator has three synthetic cases. It proves deterministic
  invariants, not generalization or outreach success.
- A manual edit invalidates the generated map but does not automatically create
  a sentence-level map for new prose; the user must inspect it before copying.
- The server replays bounded discovery rather than loading a durable saved-search
  snapshot, so rapidly changing upstream results can invalidate an old browser
  selection.
- The adapter is tested against owned HTTP fixtures; no paid live model request
  is part of the automated suite.
- The application copies text only. Sending, bulk outreach, reply tracking, and
  guessed emails are deliberately absent.

### Next step

Phase 9 should replace the fictional opportunity and tracker path with verified
opportunity ingestion, explicit source/last-verified/stale metadata, allowlisted
controlled extraction only for documented gaps, and durable application status
history. The source policy and state-transition model should be planned before
implementation.
