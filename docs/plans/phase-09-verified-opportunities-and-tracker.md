# Phase 09 — Verified opportunities and application tracker

**Status:** Complete

**Prepared:** 2026-08-01

**Scope:** Replace the fictional-only opportunity and application surfaces with
a live, source-linked opportunity search and an owner-scoped durable tracker.
The phase uses a documented public employer job API, preserves unknown facts as
`Unclear`, records provenance and freshness, and requires every save and status
change to be an explicit user action. The existing recruiter demo remains
available as a separate mode.

## 1. Outcome

At the end of this phase:

1. a student can search a small allowlist of research organizations by topic;
2. the backend retrieves published listings from the documented Greenhouse Job
   Board GET API, without scraping general web pages or accepting user-supplied
   source URLs;
3. deterministic rules admit only internship, studentship, fellowship, and
   research-assistant-style opportunities instead of presenting every job on a
   board;
4. every result retains its source record ID, source and application URL,
   organization, retrieval time, last-verified time, source kind, and evidence
   confidence;
5. work mode, funding, deadline, duration, and eligibility remain `Unclear` when
   the source does not state them explicitly;
6. stale and expired states are derived from timestamps and explicit deadlines,
   never guessed by an LLM;
7. the student can save or remove an opportunity idempotently;
8. a saved opportunity can be added to the durable application tracker once;
9. status, private notes, and follow-up date updates use optimistic versioning
   and append an immutable event history; and
10. no route submits an application, sends email, or claims that a user action
    occurred outside Research Bridge AI.

Ranking and recommendation quality remain deferred. The live result order is a
transparent freshness-first deterministic order, not a suitability score.

## 2. Starting state and preservation

- Phase 8 is committed as `98f09fb`; the working tree was clean when this plan
  began.
- Phase 5 already created `opportunities`, `saved_items`, `applications`,
  `application_events`, and shared `provenance_records`. These concepts and
  relationships are reusable, but no repository, service, or route currently
  exercises the opportunity/tracker tables.
- `Opportunity` already stores source identity, title, organization,
  description, country/location, work mode, funding, availability, deadline,
  source/application URLs, and last verification time.
- The opportunity model does not yet retain opportunity kind, research fields,
  duration, eligibility, source kind, source update time, or evidence confidence.
- `SavedItem` already has an exactly-one-target constraint and owner-target
  uniqueness. It can be reused without changing its domain meaning.
- `Application` and `ApplicationEvent` already model explicit status, notes,
  follow-up date, version, and append-only status history. Applications need
  owner-target uniqueness so repeated tracking requests cannot create duplicates.
- `/opportunities` and `/applications` currently use typed fictional fixtures and
  tab-scoped `sessionStorage`. Those flows are valuable recruiter demonstrations
  and must remain visibly fictional and isolated from live persistence.
- The approved teal + indigo design system, data-state components, generated API
  client pipeline, request transactions, structured errors, demo owner, and E2E
  harness are reused.
- No existing `.env`, secret, private resume, generated outreach body, or
  unrelated user work may be committed.

## 3. Source audit and decision

### 3.1 Selected source: Greenhouse Job Board API

Greenhouse documents that published Job Board data is public and that its GET
endpoints require no authentication. Its list endpoint returns JSON with a
stable job ID, title, location, update time, public application URL, optional
description content, departments, offices, and exposed metadata:

```text
GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
```

Phase 9 enables only a repository-owned allowlist of research organizations,
starting with:

- `thealleninstitute` — Allen Institute for AI (Ai2);
- `constructorknowledgelabs` — Constructor Knowledge Labs;
- `centerforstrategicandinternationalstudiesinc` — Center for Strategic and
  International Studies; and
- `verainstituteofjustice` — Vera Institute of Justice.

An operator may enable a subset of those identifiers. Configuration cannot add
an arbitrary host or board token. The outbound client has one fixed HTTPS origin,
does not follow redirects, and never requests a URL supplied by the browser.

The source is classified as `official-ats`: an organization publishes the record
through its own applicant-tracking board. The Greenhouse URL is both the evidence
page and the user-controlled application destination. Research Bridge AI reads
only GET endpoints and never proxies Greenhouse's application-submission POST.

### 3.2 Rejected for this phase

- **EURAXESS:** functionally relevant, but its current `robots.txt` disallows
  automated access under `/jobs/*`, including the search/detail paths needed by
  an extractor. Respecting source rules takes priority over coverage.
- **jobs.ac.uk:** its current terms allow personal copying but prohibit
  reproducing site material without permission. It is not used as an ingestion
  source.
- **USAJOBS:** the API requires a registered key and its current terms scope use
  to the registered organization unless additional written approval is granted.
  It is also a weak default for an international student because eligibility is
  frequently citizenship-restricted. A separately approved adapter can be added
  later.
- **NSF REU directory:** valuable official evidence, but typical participant
  eligibility is limited to U.S. citizens, nationals, or permanent residents,
  and the directory does not provide the same documented read API. It is not a
  default source for this student's first live slice.

These exclusions are deliberate architecture decisions, not missing features.

## 4. Product decisions

### 4.1 Evidence before completeness

The UI uses `Unclear`, not a positive-looking fallback, for an unstated work
mode, funding status, deadline, duration, eligibility detail, or country. A
published job is treated as open only at the time its successful board response
is retrieved. The app does not infer visa eligibility, professor sponsorship,
selection probability, or funding from organization reputation.

### 4.2 Deterministic opportunity inclusion

Greenhouse boards contain non-research roles. A versioned policy admits a record
only when the normalized title contains an explicit opportunity signal such as
`intern`, `studentship`, `fellowship`, `research assistant`, or an equivalent
configured phrase. Topic matching then searches the normalized title,
description text, department names, and location.

This is classification and filtering, not ranking. The policy version and the
matched signal are retained in the normalized result so the decision can be
explained and tested.

### 4.3 Bounded explicit-field extraction

The source description is HTML. A standard-library parser converts only the
allowed text content into bounded plain text. Deterministic labelled-pattern
extractors may retain:

- an explicit duration such as `Duration: 12 weeks`;
- an explicit deadline when a labelled unambiguous date is present;
- a short eligibility/requirements excerpt;
- an explicit work mode such as remote, hybrid, on-site, or in-person; and
- explicit funded/paid or unpaid wording.

Ambiguous or conflicting text returns `Unclear`. Raw HTML is never rendered in
the frontend, and no LLM expands or interprets the listing.

### 4.4 Freshness and expiry are different

- `lastVerifiedAt` is the successful retrieval time, not the source's update
  time.
- `sourceUpdatedAt` retains the provider timestamp separately.
- `isStale` becomes true when verification is older than the configured seven-day
  threshold.
- `isExpired` becomes true only when an explicit deadline is before today's UTC
  date.
- A missing deadline is `Unclear`, not “rolling” and not “open forever.”
- A provider failure is reported as a partial or full source failure. The app
  does not silently replace it with an apparently fresh cached listing.

### 4.5 Human-owned tracker transitions

An application record is only created when the student explicitly chooses
`Track application` on an already saved opportunity. Creation starts at `Saved`
and appends event 1. Updates include `expectedVersion`; a stale editor receives a
409 conflict instead of overwriting newer notes or status.

Allowed state transitions are explicit and user-directed:

```text
Saved -> Drafting | Applied | Closed
Drafting -> Saved | Ready for review | Applied | Closed
Ready for review -> Drafting | Applied | Closed
Applied -> Interviewing | Closed
Interviewing -> Applied | Closed
Closed -> Saved
```

`Applied` is never assigned automatically. Notes-only and follow-up-only updates
append a same-status event so the history remains a complete audit trail.

## 5. Reuse, extension, and non-reuse

### Reuse unchanged

- owner, request transaction, error envelope, request ID, and database session;
- `SavedItem`, `Application`, and `ApplicationEvent` domain concepts;
- shared provenance records and source-linked entity IDs;
- async HTTP client, bounded retry, timeout, and runtime lifecycle patterns;
- generated OpenAPI/TypeScript client and Zod response validation;
- TanStack Query, React Hook Form, responsive data states, and UI tokens; and
- the separate fictional recruiter demo.

### Extend selectively

- enrich `Opportunity` with source/extraction fields required by the product
  contract;
- add owner-target uniqueness to applications;
- add a typed Greenhouse provider, normalized opportunity contract, repository,
  service, dependency composition, runtime, and routes;
- add save/list/remove and create/list/update tracker operations;
- add live/demo tabs to both frontend pages rather than regenerating them;
- extend the isolated E2E source stub and critical journey; and
- update the migration, OpenAPI artifact, README, roadmap, and learning log.

### Do not reuse

- fixture opportunity IDs, `example.org` sources, or session tracker data in the
  live path;
- the demo reducer as durable persistence;
- arbitrary user-provided domains or board tokens;
- raw provider HTML in React;
- keyword hits as numeric relevance scores;
- an LLM for filtering, field extraction, status changes, or database writes;
- an external application submission API; or
- Google Scholar, EURAXESS, jobs.ac.uk, or uncontrolled university scraping.

## 6. Architecture

```text
POST /api/v1/opportunities/search
  -> opportunity route
  -> OpportunityService.search
      -> GreenhouseOpportunityProvider protocol
          -> fixed-origin async HTTP client
          -> bounded parallel GETs for enabled allowlisted boards
          -> typed response validation
      -> deterministic HTML-to-text normalization
      -> deterministic opportunity inclusion + explicit-field extraction
      -> OpportunityRepository.persist
          -> opportunity upsert + provenance upsert
      -> deterministic query/field filters and freshness-first ordering
  -> source health + typed opportunities
  -> generated TypeScript client + runtime Zod validation
  -> live opportunity workspace

POST/DELETE /api/v1/opportunities/{opportunity_id}/save
  -> route -> service -> owner-scoped repository -> idempotent save/remove

POST /api/v1/applications
  -> route -> ApplicationTrackerService.create
  -> verify owner saved the opportunity
  -> idempotent owner-target application + event 1

PUT /api/v1/applications/{application_id}
  -> route -> service -> owner-scoped repository
  -> validate transition + expected version under row lock
  -> update snapshot + append event N
```

Dependency direction remains:

```text
route -> service -> repository / provider protocol
provider adapter -> fixed-origin external HTTP client
service -> pure normalization, filtering, freshness, and transition rules
```

## 7. Public API

### `POST /api/v1/opportunities/search`

Request fields:

- `query`: 2–160 characters;
- `countryCode`: optional two-letter code;
- `workMode`: optional `on-site | hybrid | remote | unclear`;
- `funding`: optional `funded | unfunded | unclear`;
- `includeExpired`: boolean, default false; and
- `limit`: 1–30, default 20.

Response fields include `results`, source-health summaries, partial-failure flag,
policy version, retrieval time, and no ranking score. Each result includes:

- stable internal opportunity UUID;
- source name/kind/record ID and evidence confidence;
- title, organization, type, description excerpt, fields, country, and location;
- work mode, funding, availability, duration, eligibility, and deadline with
  `Unclear` represented explicitly;
- source URL and official application URL;
- source update and last verification timestamps;
- stale/expired flags; and
- deterministic inclusion/extraction evidence.

### Save endpoints

- `POST /api/v1/opportunities/{id}/save` is idempotent and returns the saved
  record;
- `DELETE /api/v1/opportunities/{id}/save` is idempotent and returns no content;
  and
- `GET /api/v1/opportunities/saved` returns only the current owner's saves.

### Tracker endpoints

- `POST /api/v1/applications` accepts one saved `opportunityId`, creates or
  returns its current tracker record, and never submits externally;
- `GET /api/v1/applications` returns current-owner records and complete ordered
  event history; and
- `PUT /api/v1/applications/{id}` accepts status, notes, follow-up date, and
  `expectedVersion` and returns the next version.

Missing or other-owner records return 404. Invalid transitions return 409 with
allowed next states. Stale versions return 409. Validation uses the existing
typed 422 envelope.

## 8. Provider safety and reliability

- fixed `https://boards-api.greenhouse.io` base origin;
- hardcoded board registry, with settings limited to a subset of that registry;
- no redirects, proxy inheritance, cookies, credentials, POSTs, or user URLs;
- explicit connect/read/write/pool timeouts and connection limits;
- at most three attempts for idempotent 429 and 5xx failures with capped backoff;
- bounded board count, result count, HTML length, plain-text length, and excerpt
  length;
- provider payload validation before normalization;
- source-specific failures surfaced without broad silent exception handling;
- no raw HTML rendering or persistence; and
- safe logs containing board key, status category, and request ID, never notes or
  profile contents.

## 9. Persistence and migration

Extend `opportunities` with:

- `opportunity_type` string;
- `research_fields` JSON list;
- `duration_text` nullable string;
- `eligibility_text` nullable text;
- `source_kind` string;
- `evidence_confidence` string;
- `source_updated_at` nullable timestamp; and
- `extraction_evidence` JSON list.

Existing source identity uniqueness remains the idempotency key. Provenance
records retain the provider URL, retrieval/verification times, a normalized
content hash, and the field names contributed by the source.

Add uniqueness for `(owner_id, opportunity_id)` and `(owner_id, author_id)` on
applications. The existing exactly-one-target and positive-version constraints
remain. Migration `0004` must upgrade and downgrade cleanly on SQLite and
PostgreSQL, and model/migration drift tests must remain green.

## 10. Frontend experience

### Opportunities

The page defaults to a live tab and keeps the fictional recruiter demo in a
second tab. The live workspace provides:

- a compact topic search plus optional country, work mode, and funding filters;
- loading, empty, full failure, partial-source, success, stale, and expired states;
- responsive evidence cards with strong hierarchy, teal evidence accents, and
  indigo actions;
- visible `Unclear` badges instead of absent values;
- source organization, last verification, official application, and inspection
  links;
- save/remove and track controls with keyboard-accessible status announcements;
  and
- no score, “best match,” or selection-probability language.

### Applications

The tracker page also defaults to a live tab and retains its local fictional
demo. The live view provides:

- an empty state linked to opportunity search;
- durable current status, notes, follow-up date, version, source link, and full
  event history;
- React Hook Form + Zod validation;
- explicit valid next-state options;
- update loading, error, stale-conflict, and success states; and
- a prominent explanation that `Applied` means only that the user recorded the
  action—it does not mean the platform submitted anything.

On mobile, forms and cards remain single-column, controls have at least 44px
targets, long source text wraps, event order remains readable, focus is visible,
and no horizontal overflow is introduced. Motion is limited to meaningful state
changes and respects reduced motion.

## 11. Tests

Backend tests cover:

- settings origin/allowlist validation;
- typed provider success, timeout, rate limit, retry, malformed payload, and
  per-board partial failure;
- HTML-to-text safety and bounded extraction;
- title-based inclusion and query/filter behavior without a score;
- ambiguous funding/work mode/deadline returning `Unclear`;
- persistence idempotency, provenance, last verification, stale and expired
  derivation;
- owner-scoped idempotent save/remove/list;
- tracker creation requires a saved opportunity and is owner-target idempotent;
- valid and invalid transitions, same-status note changes, follow-up dates,
  optimistic conflicts, and ordered history;
- migration upgrade/downgrade and constraints; and
- absence of application-submission or email-send routes.

Frontend tests cover:

- request/response runtime validation;
- live/demo mode separation;
- filter serialization and all data states;
- `Unclear`, stale, expired, source, verification, and partial-source rendering;
- save/remove/track actions and query invalidation;
- tracker empty/loading/error/success/conflict states;
- form validation, next-state options, notes/follow-up update, and event history;
  and
- no submit-application or send-email action.

E2E uses an owned loopback Greenhouse fixture server and proves:

```text
live opportunity search
  -> inspect evidence and Unclear fields
  -> save opportunity
  -> track application at Saved
  -> update notes, follow-up, and status
  -> reload tracker and retain versioned history
```

Automated tests never depend on a current external listing or make a third-party
application request.

## 12. Quality gates

Backend:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app scripts
uv run pytest
uv run python -m scripts.export_openapi --check
uv run alembic check
```

Frontend:

```bash
npm run api:check
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

Also run the PostgreSQL migration upgrade/downgrade/upgrade gate, Compose config,
production dependency audit, secret/private-file audit, and full Git diff review.
Manually verify a live provider query plus 390px and desktop layouts when network
access is available.

## 13. Explicit non-goals

- relevance ranking, personalized scoring, or ranking evaluation;
- OpenSearch, pgvector retrieval, Redis, Celery, LangGraph, or microservices;
- arbitrary ATS discovery or user-configured source URLs;
- EURAXESS, jobs.ac.uk, Google Scholar, or general web scraping;
- application form submission, resume upload, email sending, or calendar writes;
- automatic status changes inferred from email or external sites;
- guessed funding, deadline, eligibility, visa support, availability, or work
  mode;
- authenticated multi-user security guarantees (Phase 10); and
- claiming the small allowlist represents all universities or all fields.

## 14. Risks and mitigations

- **Board churn:** board failures are isolated, partial state is explicit, and
  fixtures own the automated tests.
- **Non-research jobs:** versioned title-signal admission runs before topic
  filtering and is covered by negative fixtures.
- **Misleading extraction:** labelled bounded patterns only; ambiguity becomes
  `Unclear`; source text remains linked.
- **Stale or removed listing:** verification time and stale state are separate
  from source update time; disappearance is not silently described as closed.
- **SSRF or source expansion:** fixed host plus repository-owned board registry;
  no browser URL reaches HTTPX.
- **Duplicate saves/applications:** database uniqueness plus idempotent service
  operations.
- **Lost tracker edits:** owner scoping, expected versions, row locking, and
  immutable events.
- **Recruiter confusion:** UI exposes source policy, deterministic extraction,
  unknowns, no score, and no-submit boundary.

## 15. Acceptance criteria

Phase 9 is complete only when:

- at least one allowlisted live source can return normalized research
  opportunities through a documented public GET API;
- arbitrary hosts/tokens and application POSTs are impossible through the app;
- non-research board jobs are excluded deterministically;
- every displayed record has provenance, source/application URL, and verification
  time;
- unknown fields remain visibly `Unclear`;
- stale and expired states are deterministic and distinct;
- save/remove operations are durable and idempotent;
- tracker creation is explicit, durable, owner-scoped, and deduplicated;
- every tracker edit is version-checked and appended to history;
- the live and fictional experiences are clearly separated and responsive;
- all applicable quality gates pass;
- `ROADMAP.md`, `README.md`, and `docs/LEARNING_LOG.md` are updated; and
- the full diff contains no secret, private generated data, or unrelated user
  work.

## 16. Exact next step

Plan Phase 10 around authentication, trust boundaries, user isolation, deletion,
and a threat model. Ranking remains deferred until after the placement release.

## 17. Verification evidence

- Greenhouse is accessed only through its documented public Job Board GET API,
  a fixed official origin, and four repository-owned board identifiers.
- The backend implements typed provider models, bounded HTML-to-text
  normalization, deterministic research-title admission, labelled fact
  extraction, provenance upserts, idempotent saving, and an owner-scoped
  versioned tracker.
- The frontend makes the live flow the default and retains the fictional
  recruiter flow in a clearly labelled second tab. Its forms use React Hook
  Form and Zod; server state uses TanStack Query; loading, empty, error, partial,
  stale, expired, and explicit `Unclear` states are visible.
- The browser journey covers search, save, track, status/note/follow-up update,
  event history, and persistence after reload without submitting externally.
- 81 backend tests, 39 frontend tests, and 9 Playwright journeys passed. Ruff,
  formatting, mypy, OpenAPI drift, both existing evaluators, frontend
  lint/type/API drift/build, and Compose configuration also passed.
- Revision `0004` completed an isolated PostgreSQL upgrade, downgrade to
  `0003`, re-upgrade, and Alembic schema-drift check with no new operations.
- The production dependency audit found one high-severity transitive `nanoid`
  issue. A root override and lockfile update pin it to `3.3.18`; the final
  production lockfile audit reports zero vulnerabilities and a dry run changes
  only that package.

### Source-policy references

- Greenhouse Job Board API: <https://developer.greenhouse.io/job-board.html>
- EURAXESS job search and automation policy:
  <https://euraxess.ec.europa.eu/jobs/search> and
  <https://euraxess.ec.europa.eu/robots.txt>
- jobs.ac.uk terms: <https://www.jobs.ac.uk/legal/terms-and-conditions>
- USAJOBS API reference: <https://developer.usajobs.gov/api-reference/>
- NSF REU eligibility context:
  <https://www.nsf.gov/funding/initiatives/reu>
