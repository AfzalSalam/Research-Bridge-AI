# Phase 08 — Evidence-grounded outreach

**Status:** Complete

**Prepared:** 2026-08-01

**Scope:** Turn one human-selected live researcher and one or two selected
supporting papers into an editable, versioned outreach draft. Generation is
bounded by server-retrieved profile and publication evidence, validated after
generation, persisted with provenance, and protected by an explicit human-review
step. No email address is guessed and no email is sent.

## 1. Outcome

At the end of this phase:

1. a student must first search for researchers and select exactly one candidate;
2. the student must select one or two of that candidate's supporting papers;
3. the backend re-resolves those IDs from the live discovery path instead of
   trusting names, abstracts, or profile claims supplied by the browser;
4. a versioned prompt may create a structured draft when a server-only OpenAI
   API key is configured;
5. the application uses a deterministic evidence-aware template when the model
   is disabled, unavailable, refuses, times out, returns invalid structure, or
   fails the grounding audit;
6. every response identifies its generation mode, prompt/template version,
   provider and model when applicable, and a non-secret fallback reason;
7. the UI shows the exact student facts and papers connected to customized
   claims, plus warnings for unknown contact, title, institution, availability,
   funding, and title-only evidence;
8. drafts are persisted under the current owner, edits create durable numbered
   revisions, and stale write attempts are rejected with an explicit conflict;
9. manual edits visibly mark the generated claim map as needing re-review;
10. copying is available only after the student acknowledges review of the
    current editor content; and
11. no route, database field, UI action, provider tool, or connector sends email.

## 2. Starting state and preservation

- Phase 7 is committed as `9e1bcf7`; the working tree was clean when this plan
  began.
- Live `POST /api/v1/discovery/mentors` already retrieves and persists OpenAlex
  paper/author evidence, groups candidate identities, and exposes stable internal
  UUIDs for candidates and papers.
- The profile service returns a saved profile when present and otherwise the
  visibly fictional placement profile. Authentication and true user isolation
  remain Phase 10 work.
- Phase 5 already created `outreach_drafts` and `draft_papers`, including owner,
  recipient, body, selected facts, generation metadata, timestamps, and a draft
  version counter. These tables are reusable but currently have no repository or
  live API.
- The existing demo route builds a deterministic fictional draft. It is useful as
  a product and UI reference, but its fixture identities, schemas, state, and
  `phase-04.v1` template must remain isolated from live records.
- The existing live mentor detail ends with a Phase 8 placeholder. Its candidate
  and paper selection context can be extended without regenerating the approved
  frontend.
- No dependency is needed for the model call: the existing async HTTP client is
  sufficient for a small provider adapter and avoids coupling the domain service
  to an SDK.
- No existing user profile, `.env`, secret, resume, private generated output, or
  unrelated work may be committed.

## 3. Product decisions

### 3.1 Selection is server-verified

The creation request contains only the original query, the selected candidate
UUID, one or two paper UUIDs, and a generation preference. The outreach service
reruns the existing mentor-discovery service and rejects IDs not present in that
bounded result. The browser cannot introduce a fabricated paper abstract,
recipient name, institution, or student achievement.

This repeats a cached discovery call in normal use. The small cost is preferable
to trusting security-sensitive evidence from the client; later workflow state or
authenticated saved searches can remove that repetition.

### 3.2 The model composes; deterministic code controls

Deterministic code owns:

- candidate and paper selection validation;
- the evidence package;
- allowed profile fields;
- title-only paper handling;
- prompt version selection;
- structured-output validation;
- evidence-reference validation;
- final body assembly safeguards;
- fallback selection;
- persistence, ownership, versions, and review state.

The optional LLM may only compose bounded outreach prose. It cannot retrieve,
rank, infer contact details, select evidence, calculate scores, write directly to
the database, or send a message.

### 3.3 One reliable provider, optional by configuration

The first live provider uses the OpenAI Responses API through a narrow protocol.
The default model is configurable and starts with `gpt-5.6-terra`, the current
balanced GPT-5.6 tier documented for intelligence/cost trade-offs. The request
uses low reasoning and strict structured output because this is a short bounded
writing task, not an agentic research problem.

The key is read only from server settings. If it is absent, the provider is not
constructed and deterministic fallback is an expected product mode, not an
error. The API response never returns a key, raw provider body, hidden reasoning,
or private prompt content.

### 3.4 Title-only evidence stays title-only

For a selected paper with no validated abstract, even an otherwise valid LLM
result cannot supply a method, result, or technical summary. The final connection
for that paper is generated deterministically from title, year, and visible topic
metadata and explicitly says that only title-level evidence was available.

For an abstract-backed paper, the model may create a concise connection but must
return that paper's exact ID. The claim mapper then links the passage to the
selected paper.

### 3.5 Editable means versioned, not silently overwritten

The current draft row remains the convenient latest snapshot. A new revision
table stores version 1 and every later subject/body edit. Update requests include
`expectedVersion`; the repository takes a row lock and rejects a stale version
with HTTP 409. A manual edit sets the evidence-map status to
`manual-edit-needs-review` because a mapping produced for generated prose cannot
automatically certify new user-written claims.

### 3.6 Review is a use gate, not a sending feature

The editor requires an explicit review acknowledgement before copying the current
subject and body. Any edit clears that acknowledgement. There is intentionally no
recipient email field input, send button, Gmail/Outlook connector, mail transport,
or bulk-selection behavior.

## 4. Reuse, extension, and non-reuse

### Reuse unchanged

- Phase 6 OpenAlex retrieval, normalization, cache, provenance, and persistence;
- Phase 7 mentor discovery, stable candidate/paper IDs, evidence strength, and
  uncertainty;
- profile and owner services;
- request transaction, error envelope, request ID, and generated client pipeline;
- existing `outreach_drafts` and `draft_papers` concepts;
- UI design tokens, `DataState`, `StatusBadge`, `EvidenceLink`, field primitives,
  and responsive master-detail structure; and
- the deterministic fictional demo as an offline recruiter journey.

### Extend selectively

- add live outreach schemas, service protocols, provider adapter, repository,
  dependency composition, and routes;
- add claim evidence and grounding-status fields to the current draft snapshot;
- add an immutable revision table and migration;
- extend the live candidate detail with paper selection and a writer-focused
  drafting panel;
- add live API adapters and runtime Zod validation;
- extend E2E coverage through create, edit, review, and copy; and
- add an outreach grounding/fallback evaluation report.

### Do not reuse

- fixture IDs, fictional biographies, fictional contact details, or demo prose in
  the live path;
- client-supplied profile or publication evidence;
- generated relevance explanations as paper-method evidence;
- an authorship affiliation as a current institution claim;
- the demo reducer as live persistence;
- Google Scholar scraping or any new academic source; or
- an email connector or automated send capability.

## 5. Architecture

```text
POST /api/v1/outreach/drafts
  -> outreach route
  -> OutreachService.create
      -> MentorDiscoveryReader.search
          -> cached OpenAlex retrieval + persistence
          -> deterministic candidate derivation
      -> ProfileReader.get_profile
      -> deterministic selection validator
      -> deterministic EvidencePackage builder
      -> DraftGenerator protocol
          -> optional OpenAI Responses provider
          -> strict structured composition
      -> GroundingAuditor
          -> validate student fact keys
          -> validate selected paper IDs
          -> replace title-only connections deterministically
          -> reject unsupported or malformed composition
      -> deterministic fallback on any bounded provider failure
      -> OutreachRepository.create
          -> current draft + paper links + revision 1
  -> typed response
  -> generated TypeScript client + Zod validation
  -> evidence-assisted editor

PUT /api/v1/outreach/drafts/{draft_id}
  -> route -> service -> owner-scoped repository
  -> check expected version under row lock
  -> update latest snapshot + append revision N
  -> mark claim map manual-edit-needs-review
```

Dependency direction remains:

```text
route -> service -> repository / mentor/profile protocols / model protocol
service -> pure prompt, fallback, and grounding modules
provider adapter -> outbound HTTP client
```

## 6. Public API

### `POST /api/v1/outreach/drafts`

Request:

```json
{
  "query": "interpretable machine learning for clinical decision support",
  "mentorId": "author-uuid",
  "paperIds": ["paper-uuid"],
  "generationPreference": "auto"
}
```

Rules:

- `query`: 3–300 characters, matching discovery;
- `mentorId`: UUID;
- `paperIds`: one or two unique UUIDs;
- `generationPreference`: `auto` or `deterministic`;
- `auto` attempts the configured model and safely falls back;
- `deterministic` never calls the model; and
- the candidate and every paper must exist in a server-resolved live candidate.

The response includes:

- draft ID and version;
- recipient display name, contact `null`, author source URL, and last verified time;
- subject and editable body;
- selected student facts as key/label/value records;
- selected paper evidence with source URLs and evidence strength;
- claim-to-evidence mappings with typed references;
- uncertainty warnings;
- evidence-map status;
- generation mode, provider/model, prompt/template version, and fallback reason;
- created and updated timestamps; and
- `canSend: false` as an explicit contract invariant.

### `PUT /api/v1/outreach/drafts/{draft_id}`

Request:

```json
{
  "subject": "Edited subject",
  "body": "Edited body...",
  "expectedVersion": 1
}
```

The response returns the updated draft at version 2. A mismatched version returns
`409 draft_version_conflict`, a missing or other-owner draft returns 404, and an
invalid body returns the normal typed 422 envelope.

### `GET /api/v1/outreach/drafts/{draft_id}`

Returns the owner-scoped current snapshot and available revision summaries so a
refresh does not lose the artifact. It does not expose other owners' records.

## 7. Structured generation and prompt versioning

Prompt `outreach-grounded.v1` uses a concise developer instruction and a JSON
evidence package. It asks for:

- a subject;
- a short introduction using listed student fact keys;
- exactly one connection per selected paper, keyed by paper UUID;
- a respectful question about possible student contribution;
- a closing; and
- the student fact keys used.

The provider must return a strict schema. Unknown fields are rejected. The prompt
states each safety boundary once: use only supplied facts; never invent title,
institution, contact, availability, funding, findings, or supervision; treat
title-only papers cautiously; make no acceptance or response prediction.

The provider call uses:

- Responses API;
- `store: false`;
- configurable official HTTPS origin;
- server-only bearer authentication;
- explicit connect/read/write/pool timeouts;
- at most two attempts for retryable rate-limit or server failures;
- a bounded output token limit;
- low reasoning effort and low verbosity; and
- strict JSON-schema output.

The app stores only non-secret provider/model/prompt metadata, not hidden
reasoning or raw provider payloads.

## 8. Grounding audit

A provider result is accepted only when:

1. the top-level structure passes Pydantic validation;
2. the paper connection IDs exactly match the selected paper IDs with no
   duplicates or omissions;
3. every returned student fact key is in the server-owned allowlist;
4. subject and sections meet bounded length and control-character rules;
5. each mapped claim points to at least one selected paper or allowed profile
   fact;
6. title-only paper prose is replaced by the cautious deterministic connection;
7. the final assembled body contains the selected recipient and signoff without
   adding contact data; and
8. the structural unsupported-claim rate is zero.

Any failure discards the model composition and persists a deterministic draft
with a safe fallback reason. The invalid model output itself is not returned to
the browser or logged.

## 9. Deterministic fallback

Template `outreach-template.v1` produces a professional, concise email using only:

- recipient display name;
- student name, program, institution, interests, project title/summary, skills,
  and weekly availability from the server profile;
- selected paper title, year, venue, topics, and validated abstract availability;
- cautious title-only wording; and
- a question about whether a student contribution could be useful.

The fallback is intentionally good enough for the complete demo. The model is an
optional writing improvement, not a single point of failure.

## 10. Persistence and migration

Extend `outreach_drafts` with:

- `claim_evidence` JSON;
- `evidence_map_status` string;
- `fallback_reason` nullable string; and
- `reviewed_at` nullable timestamp reserved for a later authenticated server-side
  review action (the Phase 8 copy acknowledgement remains client-local).

Add `outreach_draft_revisions` with:

- UUID primary key;
- draft foreign key with cascade delete;
- positive version;
- subject and body snapshot;
- claim evidence snapshot;
- evidence-map status;
- editor owner foreign key;
- created timestamp; and
- unique `(draft_id, version)`.

Migration `0003` upgrades and downgrades cleanly on SQLite test databases and
PostgreSQL. Existing drafts receive safe empty/default grounding values.

## 11. Frontend experience

The live mentor detail gains a clear three-part writer flow:

1. **Select evidence** — checkbox controls on supporting papers, one or two max,
   with title-only limitations beside the selection;
2. **Generate and inspect** — create in automatic or deterministic mode and show
   provider/fallback metadata, unknown facts, selected facts, and claim links;
3. **Edit, save, review, copy** — subject input and body textarea, unsaved-change
   state, versioned save, explicit review checkbox, and copy button.

Responsive behavior:

- desktop keeps candidate evidence and the writing workspace in a readable
  vertical detail flow rather than a cramped third column;
- mobile preserves list -> candidate -> evidence selection -> editor sequence;
- long titles, names, URLs, and prose wrap without horizontal overflow;
- all selection and editor controls have labels, visible focus, keyboard access,
  live status messages, and 44px targets; and
- motion remains limited to state transitions and respects reduced motion.

There is no send button. Recipient contact is shown as `Unknown — verify on an
official source` and the copy gate explains that copying is not sending.

## 12. Tests and evaluation

Backend tests cover:

- create requires one valid mentor and one or two unique selected papers;
- client-invented or mismatched IDs are rejected;
- provider-disabled deterministic generation;
- valid structured provider generation;
- timeouts, rate limits, provider refusal, invalid JSON, invalid schema, invalid
  IDs, and unsupported fact keys fall back safely;
- title-only paper output never contains model-authored method/result prose;
- claim mappings contain only allowed evidence;
- provider metadata and fallback reasons are secret-safe;
- create/read/update persistence and revision history;
- owner scoping and stale-version conflict;
- migration upgrade, model drift, constraints, and downgrade; and
- no API route or model represents sending.

Frontend tests cover:

- paper selection max-two behavior;
- generate loading, error, deterministic, LLM, and fallback states;
- runtime response validation;
- visible claims, evidence links, warnings, and generation metadata;
- editing clears review acknowledgement;
- save updates the visible version;
- copy is disabled before review and enabled after review; and
- contact unknown and absence of a send action.

E2E covers the deterministic path so it is stable without paid services:

```text
live mentor search
  -> select candidate
  -> select supporting paper
  -> generate deterministic draft
  -> edit subject/body
  -> save version 2
  -> acknowledge review
  -> copy-ready state
```

A fixture evaluator reports generation success, deterministic fallback coverage,
grounding acceptance, unsupported-reference rate, title-only safety, and bounded
generation/audit latency. It is labelled as a small structural evaluation, not a
measurement of email reply or selection probability.

## 13. Quality gates

Backend:

```bash
uv run ruff check .
uv run mypy app
uv run pytest
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

Also run the PostgreSQL migration gate and the repository secret/private-file
audit already established by earlier phases. Manually verify desktop, 390px
mobile, keyboard focus, long-content wrapping, fallback metadata, and review
reset after editing.

## 14. Explicit non-goals

- automatic or direct email sending;
- Gmail, Outlook, SMTP, or bulk outreach integration;
- contact discovery or guessed email patterns;
- professor title/current-employer verification;
- new academic providers or web extraction;
- tracking replies, acceptance, funding, or response probability;
- authentication or real multi-user privacy guarantees;
- LangGraph orchestration;
- prompt optimization claims without a representative evaluation set; and
- Phase 9 opportunity ingestion or application tracking changes.

## 15. Risks and mitigations

- **Hallucinated prose:** strict structure, server-owned evidence, deterministic
  audit, title-only replacement, and fallback.
- **Provider outage/cost:** optional key, bounded timeouts/retries/tokens, explicit
  deterministic mode, and E2E without provider calls.
- **Client evidence tampering:** send IDs only and resolve facts server-side.
- **Stale edits:** optimistic version check plus immutable revisions.
- **Misleading claim map after editing:** switch to
  `manual-edit-needs-review` and clear the UI review gate.
- **Private data leakage:** server-only key, no prompt/body logging, no raw provider
  response persistence, and fictional fallback profile before authentication.
- **Recruiter confusion:** expose generation metadata, fallback state, evidence
  references, unknown fields, and the no-send boundary directly in the UI.

## 16. Acceptance criteria

Phase 8 is complete only when:

- one live researcher and one or two supporting papers are required;
- the server verifies every selected ID and supplies all facts itself;
- valid configured model output is structured, audited, and attributable;
- every model failure path returns a useful deterministic draft;
- title-only evidence cannot become an invented method/result claim;
- current draft plus revision history survive database round trips;
- stale edits are rejected;
- the editor visibly connects customized passages to evidence;
- editing and review/copy behavior are accessible and responsive;
- no sending capability exists;
- all applicable quality gates pass;
- `ROADMAP.md` and `docs/LEARNING_LOG.md` are updated; and
- the full diff contains no secret or unrelated owner work.

## 17. Exact next step

Begin Phase 9 with a repository and source audit for verified opportunity
ingestion. Define the allowlisted source policy, provenance/staleness contract,
and durable application-transition model before replacing the fictional
opportunity and tracker flows.

## 18. Completion evidence

- Live create/get/update contracts, strict generated client types, owner-scoped
  persistence, immutable revisions, and optimistic conflict handling are wired.
- The optional Responses API adapter is bounded and secret-safe; deterministic,
  unavailable, refusal, malformed, and grounding-failure paths are tested.
- The live mentor detail requires human paper selection and exposes generation
  provenance, claim references, uncertainty, manual-edit review invalidation,
  and copy-only approval with no send action.
- The structural grounding baseline accepts the valid case and rejects both an
  unknown reference and an unsupported availability assertion.
- Backend lint, formatting, strict typing, 67 tests, OpenAPI drift, evaluator
  drift, and migration tests passed. Frontend lint, strict typing, 33 tests,
  generated-client drift, production build, and all eight isolated Playwright
  journeys passed.
