# Phase 03 — Typed Mock Product Journey

**Status:** Complete

**Prepared:** 2026-07-31

**Scope:** A complete, deterministic, recruiter-ready frontend journey powered
only by typed fictional fixtures and browser-local demo state

## 1. Outcome

Turn the Phase 2 visual shell into a coherent placement-demo product journey
without pretending that the backend, academic APIs, ranking, an LLM, or durable
persistence exist.

At the end of this phase, a recruiter can:

1. inspect and edit a fictional student research profile;
2. run a clearly labelled simulated topic search;
3. observe honest named progress stages without fabricated percentages;
4. inspect fictional paper evidence and professor candidates;
5. select a mentor and one or two supporting papers;
6. create and edit a deterministic, evidence-linked outreach draft;
7. save a fictional opportunity;
8. track an application and update its status; and
9. reset the deterministic demo to its known initial state.

The journey demonstrates typed state, runtime validation, form architecture,
responsive master-detail UI, provenance presentation, human review, state
transitions, accessibility, and end-to-end testing. It does not claim live
intelligence.

## 2. Starting state and preservation

- Phase 2 is committed as `ed131d2` on `main`.
- The design system, route shells, navigation, data states, health contract,
  tests, and build are working.
- `apps/web/next-env.d.ts` changed from the production type path to the
  development type path after the repository owner ran `next dev`. This is a
  generated Next.js change, not authored product work. It must remain isolated
  and be rechecked after the final production build.
- No other working-tree changes existed when Phase 3 began.
- Backend and database source are outside this phase and must remain unchanged.

## 3. Product decisions

### 3.1 Demo truthfulness

- Every demo person, organization, paper, opportunity, email address, and
  outcome is visibly marked fictional.
- Reserved `example.org` URLs are used instead of links that resemble real
  academic records.
- No DOI, ORCID, OpenAlex ID, title, affiliation, contact, or availability is
  presented as real.
- Search progress says it is loading deterministic fixtures. It never claims
  to contact OpenAlex or an LLM.
- The mentor list is explicitly `Demo order — not ranked` and contains no
  numeric score, percentile, prestige filter, or response-rate estimate.
- Availability and contact remain `Unknown` unless a fictional fixture
  explicitly demonstrates a verified field.

### 3.2 Outreach behavior

- A draft becomes available only after the student selects a mentor and at
  least one paper.
- The draft is produced by a deterministic local template, not an LLM.
- The generated body may use only the selected fictional student profile and
  the selected paper title/year/topic/validated summary fields.
- The editor shows its selected facts, paper evidence, warnings, mode, and
  version.
- The user can edit, copy, save, or track the draft.
- There is no send button, email-provider integration, background action, or
  mass-contact workflow.

### 3.3 Persistence boundary

- A versioned React Context + reducer owns the demo state.
- State is mirrored to `sessionStorage` after runtime validation so navigation
  and refreshes within the tab remain useful during a recruiter demo.
- The UI states explicitly that this is browser-tab demo storage and warns the
  user not to enter private or real resume information.
- Reset restores the canonical fixture state.
- No cookies, account, backend writes, database writes, or cross-device
  persistence are introduced.

### 3.4 Search and failure states

The discovery form includes a visibly labelled demo-scenario control:

- `Complete fixtures`: papers and mentor candidates are available.
- `Partial fixture response`: results remain usable with a source warning.
- `No fixture matches`: a useful empty state is shown.
- `Simulated fixture error`: an error state with retry is shown.

This makes loading, empty, error, and partial behavior explainable and testable
without lying about external systems.

## 4. Architecture

```text
RootLayout (Server Component)
  -> DemoProvider (small client state boundary)
      -> SiteHeader
      -> route Server Component
          -> feature Client Component only where interaction is required

features/demo/
  contracts.ts       Zod schemas and inferred domain types
  fixtures.ts        canonical, visibly fictional records
  demo-reducer.ts    deterministic state transitions
  demo-store.tsx     Context, session hydration, reset, actions
  draft-template.ts  deterministic evidence-bounded draft factory

features/profile/        profile form and validation
features/discovery/      query form, progress, outcome states
features/mentors/        accessible list/detail/evidence/draft flow
features/opportunities/  fixture filters and save behavior
features/applications/   status tracker and event history
```

The backend boundary remains unchanged. Phase 4 will replace fixture access
with typed FastAPI mock contracts while preserving the visible journey.

## 5. Typed contracts

All contracts are Zod schemas with inferred TypeScript types. Persisted state
and form input are parsed at runtime rather than trusted because TypeScript
types do not exist after compilation.

### StudentProfile

- `displayName`
- `degree`
- `graduationYear`
- `researchInterests[]`
- `skills[]`
- `methods[]`
- optional `projectExperience`
- optional `locationPreference`

### PaperEvidence

- demo ID and explicit fixture label
- title, year, fictional venue
- topics
- validated fixture summary
- `evidenceLevel`: `abstract-supported` or `title-only`
- reserved source URL
- source label and fictional last-verified date

### MentorCandidate

- demo ID and explicit fixture label
- display name
- academic title or `Unknown`
- fictional institution and location
- topics
- supporting paper IDs
- evidence completeness: `Complete` or `Partial`
- availability: `Unknown`
- contact: `Unknown`
- warnings

There is deliberately no score, percentile, rank, response rate, or acceptance
claim in this contract.

### OutreachDraft

- ID, recipient mentor ID, subject, editable body
- selected student facts
- selected supporting paper IDs
- claim-to-evidence notes
- uncertainty warnings
- generation mode: `deterministic-demo`
- template version and draft version
- created/updated timestamps generated by an injectable clock

### Opportunity

- demo ID, title, fictional organization, field, country
- work mode and funding, including `Unclear`
- duration, eligibility, fictional deadline
- reserved application/source URLs
- fixture last-verified date and evidence confidence

### Application

- ID and target type
- target ID and display label
- status from a closed transition set
- notes, optional follow-up date
- linked draft ID where applicable
- ordered event history with timestamps

### DemoState

- schema version
- profile
- active query and selected demo scenario
- search outcome and completed progress stages
- selected mentor and paper IDs
- drafts
- saved opportunity IDs
- applications
- last action message

## 6. Route experience

### `/`

- Change the primary call to action from `Explore the shell` to `Launch demo`.
- Explain that the product journey is deterministic and fictional.
- Keep the real FastAPI health status separate from demo availability.

### `/profile`

- React Hook Form + Zod profile form with accessible labels and errors.
- Pre-populated fictional student fixture.
- Repeatable comma-separated list parsing for interests, skills, and methods.
- Save confirmation and clear browser-tab/privacy explanation.
- Continue action to Discover.

### `/discover`

- Topic/method/identifier query field.
- Demo-scenario selector.
- Named progress stages with no percentage.
- Complete, partial, empty, and error outcomes.
- Paper summaries with evidence level and reserved source link.
- Continue action to mentor evidence when results exist.

### `/mentors`

- Desktop: accessible result list plus evidence detail.
- Mobile: result list, then selected detail, then draft editor.
- Mentor rows are buttons with selected/current semantics.
- Explicit `Demo order — not ranked` label.
- Title, availability, and contact uncertainty remain visible.
- Paper selection controls precede draft creation.
- Deterministic draft editor exposes evidence references and warnings.
- Saving the draft creates or updates a tracked application.

### `/opportunities`

- Filter fictional opportunities by field, country, work mode, and funding.
- Show `Unclear` values rather than inferring them.
- Display reserved official/source URL, fixture timestamp, and evidence status.
- Save/unsave actions update browser-tab demo state.
- Empty filters produce the shared empty-state component.

### `/applications`

- Show a seeded fictional application plus items created by the journey.
- Update status through explicit allowed transitions.
- Edit notes and follow-up date.
- Display a chronological event history.
- Link back to mentor or opportunity evidence.
- Reset demo is available from the shared demo notice.

### `/design-system`

- Remains an internal reference and receives no product behavior.

## 7. Shared components

- `DemoNotice`: persistent visible fictional/demo label, storage boundary, and
  reset action.
- `WorkflowSteps`: Profile → Discover → Mentor → Draft → Track orientation.
- `EvidenceLink`: external/reserved source affordance with consistent icon and
  accessible text.
- `FactRow`: label/value/source/unknown semantics without card noise.
- `ProgressStages`: semantic ordered stage status without fabricated percent.
- `FormMessage`: accessible success/validation status.
- `NativeSelect`: styled semantic select until a complex select is justified.
- Existing Button, Badge, Field, Input, Textarea, StatusBadge, DataState,
  Container, and PageHeader are reused.

## 8. Dependencies and why they exist

| Dependency | Scope | Reason |
| --- | --- | --- |
| `react-hook-form` | runtime | Required repository form architecture; minimizes rerenders and manages accessible form state. |
| `zod` | runtime | Runtime validation for forms, fixtures, and session-hydrated state. |
| `@hookform/resolvers` | runtime | Connects Zod schemas to React Hook Form without hand-written error translation. |
| `@playwright/test` | development | Exercises the recruiter-critical journey in a real browser. |

TanStack Query is not added because Phase 3 has no server state. Motion is not
added because the progress and master-detail transitions remain understandable
without decorative animation.

Every new package must be locked, audited, and explained in the learning log.

## 9. State transitions

```text
profile saved
  -> query submitted
  -> fixture progress stages
  -> complete | partial | empty | error
  -> mentor selected
  -> paper evidence selected
  -> deterministic draft created
  -> draft edited
  -> application tracked
  -> application status changed
```

Reducer actions are a closed discriminated union. Invalid persisted state is
discarded and replaced with the canonical demo fixture state.

## 10. Accessibility and responsive acceptance

- One `main` and one `h1` per route.
- Demo status is conveyed by text, not color alone.
- Every form control has a programmatic label, description where needed, and
  visible validation message.
- Mentor rows and save actions are real buttons.
- Selected mentor and current navigation states are programmatically exposed.
- Progress uses an ordered list and live status text without noisy repeated
  announcements.
- Mobile follows list → detail → draft; it never squeezes desktop master-detail
  columns.
- Copy feedback uses an accessible status region.
- External fixture links say they open a source and use safe link attributes.
- No control is available for sending email.
- Focus is visible, targets remain usable at 44 CSS pixels, reduced motion is
  respected, and layouts do not scroll horizontally at 360, 390, 768, or 1280
  pixels.

## 11. Testing strategy

### Unit/component

- every canonical fixture parses;
- invalid session state is rejected;
- list parsing trims, deduplicates, and removes blanks;
- reducer transitions are deterministic;
- draft output contains only selected mentor/profile/paper facts;
- title-only evidence never produces technical-result claims;
- profile validation exposes useful errors;
- search outcome states render correctly;
- mentor selection gates draft creation;
- application transitions append history rather than replacing it.

### Playwright critical flow

1. Reset demo.
2. Save the fictional profile.
3. Search for `retrieval-augmented learning systems` using complete fixtures.
4. Confirm named progress and the `Demo order — not ranked` label.
5. Select a mentor and supporting paper.
6. Create and edit the deterministic draft.
7. Save/track it.
8. Open Applications and verify the linked evidence and edited content.
9. Change application status and verify history.
10. Verify no `Send` action exists.

The E2E server runs only the frontend; FastAPI availability is not required for
the deterministic demo routes.

## 12. Quality gates

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run test:e2e
npm.cmd run build
npm.cmd audit --omit=dev --audit-level=high

Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
Set-Location ../..

docker compose --env-file .env.example config --quiet
git diff --check
```

Browser QA inspects the complete journey at desktop and mobile sizes, keyboard
focus, URL transitions, interactive states, and horizontal overflow.

### Completed verification — 2026-07-31

- `npm.cmd run lint`: passed.
- `npm.cmd run typecheck`: passed in TypeScript strict mode.
- `npm.cmd run test`: 8 files and 17 tests passed.
- `npm.cmd run test:e2e`: production build plus 4 Playwright tests passed.
- Responsive matrix: all five product routes passed without page-level
  overflow at 360, 390, 768, and 1280 CSS pixels.
- Keyboard/reduced motion: skip-link activation, mobile navigation focus return,
  and reduced transition duration passed in Playwright.
- Manual in-app browser QA: desktop profile and mobile mentor list/detail were
  visually inspected; the active mobile workflow step is fully visible and the
  browser console had no warnings or errors.
- Backend: Ruff lint and format, mypy, and 2 pytest tests passed.
- Compose: `docker compose --env-file .env.example config --quiet` passed; the
  sandbox could not read the user's Docker client config, which did not affect
  configuration validation.
- Production npm audit: 0 vulnerabilities.
- Full npm audit: 9 high-severity Brace Expansion advisories remain in the
  ESLint-only development graph. npm proposes a breaking ESLint 10 upgrade;
  production dependencies are unaffected and the existing Phase 1 mitigation
  remains in force.
- Supported runtime remains Node 24. Local verification used Node 26.4.0 and
  emitted the expected engine warning during dependency installation.

## 13. Milestones

### A. Contracts and state

- [x] Add dependencies and scripts.
- [x] Define and test Zod domain/state schemas.
- [x] Add visibly fictional fixtures.
- [x] Add deterministic reducer, provider, session validation, and reset.
- [x] Add bounded deterministic draft factory.

### B. Shared demo language

- [x] Add DemoNotice and WorkflowSteps.
- [x] Add NativeSelect, EvidenceLink, FactRow, FieldError, and ProgressStages.
- [x] Update the landing CTA and demo explanation.

### C. Journey screens

- [x] Build and validate Profile.
- [x] Build Discover progress and all outcome states.
- [x] Build responsive Mentor list/detail/evidence selection.
- [x] Build the editable deterministic draft and tracking action.
- [x] Build Opportunity filtering and save state.
- [x] Build Application status, notes, follow-up, and history.

### D. Verification

- [x] Add focused unit/component tests.
- [x] Add the Playwright critical flow.
- [x] Pass all frontend and backend quality gates.
- [x] Verify all routes at 360, 390, 768, and 1280 pixels.
- [x] Verify keyboard and reduced-motion behavior.
- [x] Run production/full dependency audits and document results.
- [x] Update README, ROADMAP, and LEARNING_LOG.
- [x] Review the full diff and scan for secrets/private data.

## 14. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Fixtures look like live results | Persistent demo labels, fictional suffixes, reserved URLs, and explicit scenario language. |
| Mock progress implies real retrieval | Name every stage as fixture preparation and never show percentages or provider claims. |
| Demo state becomes production architecture | Keep it behind `features/demo`; Phase 4 replaces the adapter while preserving contracts. |
| Context rerenders the whole application | Split reducer actions from derived selectors where useful and keep fixture collections module-level. |
| Session storage receives private data | Warn against real data, use tab-only storage, and implement reset; authentication/private storage remain mandatory before deployment. |
| Deterministic email invents paper content | Template only validated fixture summary/topic fields and display claim-to-evidence notes. |
| A recruiter mistakes ordering for ranking | `Demo order — not ranked` appears beside every mentor result list. |
| Mobile repeats Figma's squeezed layout | Explicit list/detail modes and width-matrix browser checks. |
| Playwright adds flaky timeouts | Use role-based locators, deterministic fixture stages, and event-driven assertions. |

## 15. Rollback

- Phase 2 remains recoverable as commit `ed131d2`.
- Phase 3 is one reviewable commit after all gates pass.
- Browser-local demo state is resettable and has no external side effects.
- No backend, database, email, or third-party state is mutated.

## 16. Out of scope

- Real OpenAlex, Semantic Scholar, Crossref, ORCID, or arXiv requests.
- Numeric relevance scoring, ranking, embeddings, reranking, or evaluation.
- Real professor identities, contacts, availability, papers, or institutions.
- LLM calls, prompt infrastructure, LangGraph, or AI-generated email.
- Email sending or provider integration.
- FastAPI product routes or TypeScript API generation.
- PostgreSQL persistence, Alembic migrations, authentication, or file uploads.
- Real opportunity extraction or verification.
- Analytics, observability, deployment, dark mode, or localization.

## 17. Completion rule

Phase 3 is complete only when the deterministic fictional journey works from
profile through application tracking, all later-phase behavior remains visibly
mocked or absent, the critical Playwright flow passes, responsive/accessibility
checks pass, documentation teaches the architecture, and the full diff contains
no secrets or private data.

The exact next step is **Phase 4 — Backend contracts**: expose typed mock
services through FastAPI and replace the frontend fixture adapter without
changing the user journey.
