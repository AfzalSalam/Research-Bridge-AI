# Phase 07 — Basic relevance and evidence

**Status:** Complete

**Prepared:** 2026-08-01

**Scope:** Derive reviewable researcher candidates from the authors of live
OpenAlex paper evidence, apply one deterministic and versioned placement-release
relevance policy, expose every feature contribution and uncertainty, measure the
quality of the bounded candidate layer, and build a responsive live mentor
workspace without introducing advanced ranking research or outreach generation.

## 1. Outcome

At the end of this phase:

1. a student can enter a topic, DOI, or OpenAlex Work ID and receive researcher
   candidates derived only from authors of the supporting papers;
2. every candidate retains the exact supporting papers, authorship position,
   paper-specific affiliations, source URLs, identifiers, and verification time;
3. current academic title, current institution, contact information, funding,
   and availability remain `Unknown` unless a future verified source supplies
   them;
4. one deterministic policy creates a review order from transparent lexical
   overlap, supporting-paper depth, recent relevant activity, and publication
   evidence completeness;
5. the public contract exposes a relevance band and individual feature
   contributions, but no prestige score, acceptance probability, response-rate
   estimate, or research-grade ranking claim;
6. deterministic tie-breaking makes the same evidence, profile, policy version,
   and evaluation year produce the same candidate order;
7. complete, partial, empty, and source-error states remain explicit;
8. the live mentor UI uses the approved editorial master-detail direction on
   desktop and a list-to-detail task sequence on mobile;
9. the deterministic fictional recruiter mentor and outreach journey remains
   available as a separate mode and keeps its existing contracts;
10. fixture evaluation reports retrieval success, candidate-duplicate rate,
    evidence coverage, unsupported-claim rate, and heuristic latency without
    adding Recall, MRR, nDCG, embeddings, or reranking; and
11. the phase is explainable by a fourth-year BTech student from API call through
    candidate evidence and UI rendering.

## 2. Starting state and preservation

- Phase 6 is committed as `795945f`; the working tree was clean when this plan
  began.
- `POST /api/v1/discovery/papers` already owns query classification, bounded
  OpenAlex retrieval, normalization, deduplication, cache-aside behavior,
  persistence, provenance, and partial provider outcomes.
- The paper response already includes stable internal IDs, OpenAlex IDs, DOI,
  title, year, venue, evidence strength, topics, ordered authors, paper-specific
  affiliations, source links, and verification time.
- The stored student profile supplies explicit interests, skills, and project
  facts. Until authentication exists it remains a visibly fictional portfolio
  profile; the browser must not be encouraged to enter private data.
- `Author.academic_title` and `Author.institution_id` are nullable and currently
  unknown. They must not be filled from an authorship affiliation.
- OpenAlex work affiliations describe an author on a particular publication.
  They are useful evidence, but they are not proof of a current job.
- The existing `/mentors` experience is a polished fictional master-detail and
  draft flow. Its visual primitives can be reused, but live schemas and state
  must remain separate so real provider evidence is never mixed with fixtures.
- Phase 7 requires no database migration. Candidate relevance is derived from
  current evidence at request time; persisting searches or recommendations is
  deferred until ownership and product need justify it.
- No unrelated owner work, secret, private profile, or generated personal data
  may be changed or committed.

## 3. Product decision: basic relevance is not advanced ranking

The owner previously chose to defer “ranking things.” Phase 7 respects that
decision by implementing only the minimal placement-release prioritization
required to make a candidate list reviewable.

This phase may:

- group repeated paper authors into candidates;
- calculate deterministic, bounded feature values;
- sort candidates using a documented policy;
- expose `strong`, `promising`, or `exploratory`
  bands;
- show the exact evidence and contribution behind each feature; and
- evaluate evidence coverage and unsupported claims.

This phase must not:

- call the result a machine-learning ranking model;
- expose an unexplained overall numeric fit score;
- use citations, institution prestige, h-index, grants, or popularity;
- use embeddings, pgvector, full-text retrieval experiments, cross-encoders, or
  LLM judgment;
- tune weights against a labelled relevance dataset;
- report Recall@5/10, MRR, or nDCG; or
- predict whether a researcher will reply, supervise, fund, or accept a student.

Those experiments remain Phase 14 work and must be adopted only after measured
benefit.

## 4. Reuse, extension, and non-reuse decisions

### 4.1 Reuse unchanged

- Phase 6 `OpenAlexClient`, provider DTOs, normalization, and cache;
- `PaperDiscoveryService` as the retrieval/persistence boundary;
- stored profile reader and server-owned demo owner resolution;
- shared request ID and structured error envelope;
- generated OpenAPI TypeScript workflow and runtime Zod validation;
- design tokens, `DataState`, `StatusBadge`, `EvidenceLink`, forms, and buttons;
- the existing fictional `MentorExperience` internals and deterministic draft
  journey; and
- the isolated SQLite + loopback OpenAlex E2E harness.

### 4.2 Extend selectively

- add a pure relevance domain module with versioned policy configuration;
- add a mentor discovery service that composes paper discovery and profile
  reading without duplicating provider logic;
- add a typed live mentor route and frontend adapter;
- turn the mentors page into a live/demo mode workspace;
- add a “derive researcher candidates” transition from live paper results;
- add fixture evaluation and a checked-in quality report; and
- extend E2E fixtures so one author can be supported by multiple papers.

### 4.3 Do not reuse

- fictional mentor IDs, rationales, roles, institutions, or paper summaries as
  live evidence;
- demo reducer state as live server state;
- the deterministic outreach endpoint for real researchers before Phase 8;
- `Author.institution_id` as a shortcut for historical paper affiliations; or
- OpenAlex topic scores as student-researcher relevance scores.

## 5. Architecture

The new path remains inside the modular monolith:

```text
POST /api/v1/discovery/mentors
  -> mentor route
  -> MentorDiscoveryService
      -> ProfileReader
          -> server-owned fictional profile until authentication
      -> PaperDiscoveryReader
          -> cache / OpenAlex provider
          -> normalizer
          -> academic repository / PostgreSQL
      -> CandidateDeriver (pure deterministic code)
          -> group paper authors
          -> retain paper-specific evidence
          -> calculate versioned feature contributions
          -> assign evidence band and confidence
          -> deterministic tie-break
          -> claim-support audit and request quality metrics
  -> typed MentorDiscoveryResponse
  -> generated TypeScript adapter + runtime Zod validation
  -> live responsive mentor master-detail
```

Dependency direction:

```text
route -> service -> paper/profile protocols -> provider/repositories
                  -> pure relevance policy
```

Routes contain only transport concerns. SQL remains in repositories. Feature
calculation remains pure and independently testable. No LLM or database write
is permitted inside the relevance policy.

## 6. Public API contract

### `POST /api/v1/discovery/mentors`

Request:

```json
{
  "query": "interpretable machine learning for clinical decision support",
  "paperLimit": 20,
  "candidateLimit": 12
}
```

Bounds:

- `query`: same validated 3–300 character text/DOI/OpenAlex-ID contract as paper
  discovery;
- `paperLimit`: 1–25, default 20;
- `candidateLimit`: 1–20, default 12.

The request does not accept a user ID, arbitrary provider URL, weights, current
year, or unverified professor attributes.

Response-level fields:

- `status`: `complete`, `partial`, or `empty`;
- normalized query and query kind;
- `ordering`: `deterministic-evidence-policy`;
- `policyVersion`: `placement-relevance-v1`;
- the non-secret weights used by that policy;
- `profileMode`: `saved-or-fictional-fallback` until authentication exists;
- the profile interests/skills used as transparent inputs, excluding name and
  unnecessary private fields;
- inherited OpenAlex source/cache/rate metadata;
- paper count, author-appearance count, unique candidate count, returned count,
  and skipped/limited counts;
- request quality metrics and bounded timing fields;
- structured warnings; and
- candidates in deterministic review order.

Candidate fields:

- internal author UUID, OpenAlex ID, optional ORCID, verified display name, and
  OpenAlex source URL;
- `academicTitle: null` unless verified;
- `currentInstitution: null` unless verified by a future current-role source;
- `availability: "unknown"`;
- research themes derived from exact OpenAlex topic labels on supporting papers;
- total supporting-paper count and the bounded supporting-paper evidence list;
- `relevanceBand` without an overall numeric fit score;
- feature contributions with feature key, label, configured weight, normalized
  observed value, bounded contribution, explanation, matched terms, and
  supporting paper IDs;
- evidence completeness and `high`/`moderate`/`limited` evidence confidence;
- identity, affiliation, title-only, current-role, and availability warnings;
- source and last-verified timestamps.

Supporting-paper fields:

- internal UUID, OpenAlex ID, optional DOI, title, year/date, venue/type/language;
- abstract excerpt only when validated;
- evidence strength and exact source URL;
- OpenAlex topic labels and provider topic scores, still labelled as provider
  metadata;
- this candidate’s author position and corresponding-author flag;
- all affiliations reported for this author on this paper, each with its source;
- last-verified timestamp.

The live response does not contain an email address, draft action result,
current-role claim, or acceptance/funding estimate.

## 7. Candidate derivation

Candidate derivation is deterministic:

1. receive the normalized paper discovery response;
2. visit papers in provider order and authors in authorship order;
3. group authors by internal author UUID, which already represents conservative
   provider identity resolution;
4. retain every unique supporting paper for each author;
5. retain the affiliations on that specific paper authorship;
6. aggregate exact topic labels without rewriting them;
7. calculate relevance features from the query, fictional profile inputs, and
   supporting papers;
8. assign a relevance band and evidence confidence;
9. audit every generated factual explanation for supporting paper IDs;
10. order by internal contribution total, supporting-paper count, normalized
    display name, then UUID; and
11. return only the requested candidate limit while reporting the total derived
    count.

No author is excluded merely because title, institution, ORCID, affiliation, or
availability is unknown. A record is excluded only when it lacks the validated
author identity already required by Phase 6.

## 8. Deterministic text normalization

The relevance module uses one shared tokenizer:

- Unicode NFKC normalization;
- case folding;
- Unicode letter/number token extraction;
- stable whitespace removal;
- removal of a small, versioned English UI stopword set;
- no stemming package, synonym expansion, embeddings, fuzzy identity matching,
  or LLM expansion; and
- preservation of the original display text for UI and evidence.

Matched terms are returned so a student can see why lexical overlap was counted.
A token match is evidence of text overlap, not proof of subject-matter fit.

## 9. Versioned relevance policy

`placement-relevance-v1` has five configurable weights that sum to exactly 1.0:

| Feature | Default weight | Meaning |
| --- | ---: | --- |
| Query evidence overlap | 0.35 | Query terms visibly present in supporting paper topics, titles, or validated abstracts. |
| Profile evidence alignment | 0.25 | Verified fictional profile interest/skill/project terms visibly present in supporting publication evidence. |
| Supporting-paper depth | 0.15 | More than one independent supporting paper, saturating at three. |
| Recent relevant activity | 0.15 | Recency of the newest supporting paper relative to an injected evaluation year. |
| Publication evidence completeness | 0.10 | Availability of abstract, DOI, venue, topics, author ID, and paper-specific affiliation evidence. |

Weights live in typed server settings, are validated to the range 0–1, and must
sum to 1.0 within a small numeric tolerance. They are injectable in tests and
returned in the public policy metadata. The request cannot override them.

### 9.1 Query evidence overlap

For each supporting paper:

- topic-token coverage contributes 50%;
- title-token coverage contributes 30%; and
- validated abstract-token coverage contributes 20%.

The candidate value is a deterministic weighted mean of at most the three best
supporting-paper overlap values. The response lists the matched query terms and
paper IDs. Missing abstracts contribute zero only to the abstract portion and
produce an uncertainty warning.

### 9.2 Profile evidence alignment

The policy builds a transparent profile vocabulary from saved research
interests, skills, project title, and project summary. It compares those terms
only with supporting-paper topics, titles, and validated abstracts. Generic
stopwords do not count. The response shows matched terms and evidence IDs.

The student’s institution, name, graduation year, and weekly availability do
not affect researcher relevance.

### 9.3 Supporting-paper depth

```text
depth = min(unique supporting papers, 3) / 3
```

This rewards repeated evidence without allowing a prolific author to dominate
the policy. Citation counts and publication volume outside the retrieved query
are not used.

### 9.4 Recent relevant activity

The newest supporting-paper year receives:

- `1.00` when age is 0–2 years;
- `0.75` when age is 3–5 years;
- `0.50` when age is 6–8 years;
- `0.25` when age is 9–12 years; and
- `0.00` when older.

The evaluation year is injected by the server clock and tests use a fixed year.
Future publication years are treated as age zero but produce a metadata warning.
Recency is not prestige or quality.

### 9.5 Publication evidence completeness

Each supporting paper receives bounded completeness credit for:

- validated abstract: 0.30;
- DOI: 0.15;
- venue: 0.15;
- at least one topic: 0.15;
- stable author OpenAlex ID or ORCID: 0.15; and
- at least one paper-specific affiliation: 0.10.

The candidate value is the mean across supporting papers. Current title,
current institution, contact, and availability are not part of this feature
because missing facts must not lower “fit” or tempt the system to invent them.

### 9.6 Contribution and relevance band

For each feature:

```text
contribution = configured weight × normalized feature value
```

The internal total is used only for deterministic review ordering and banding:

- `strong`: total at least 0.70;
- `promising`: total at least 0.45 and below 0.70;
- `exploratory`: total below 0.45.

The total is not returned as a single “fit score.” Individual values, weights,
contributions, matched terms, and evidence IDs are returned so the ordering can
be reconstructed and challenged.

### 9.7 Evidence confidence

Evidence confidence describes support quality, not the probability that the
researcher is suitable:

- `high`: stable author identifier, at least two supporting papers, and
  completeness at least 0.75;
- `moderate`: stable author identifier and completeness at least 0.50;
- `limited`: all other cases.

The UI always spells this distinction out.

## 10. Unknown and provenance rules

- An author of a relevant paper is a `researcher candidate`, not automatically
  a professor.
- `academicTitle` stays `null` because OpenAlex paper authorship does not verify
  “Professor,” “Dr.,” or another current title.
- `currentInstitution` stays `null` in Phase 7.
- Paper affiliations are labelled “reported on this paper” and retain paper and
  institution source links.
- `availability` is always `unknown` until a current official source is added.
- No email address, lab opening, funding, supervision history, country
  preference, or work mode is inferred.
- A title-only paper can support an identity/topic-title connection but cannot
  support claims about methods or findings.
- Candidate explanations are deterministic templates; every factual template
  contains at least one supporting paper ID.
- Source timestamps reflect the underlying normalized evidence, not the time a
  candidate happened to be scored.

## 11. Quality measurements

The live response includes request-level, non-sensitive measurements:

- author appearances before grouping;
- unique candidate count;
- collapsed-duplicate rate;
- candidate evidence coverage;
- unsupported-claim rate from the structural claim audit;
- retrieval/persistence duration;
- pure heuristic duration; and
- total service duration.

The checked-in evaluation harness uses representative fixtures and reports:

- query cases attempted and cases producing at least one candidate;
- retrieval success rate;
- candidate duplicate rate after grouping;
- evidence coverage;
- unsupported-claim rate;
- scorer latency p50 and p95 over bounded repeated fixture runs; and
- policy version, fixture version, evaluation year, and machine/runtime note.

The report must clearly distinguish deterministic fixture/scorer measurements
from real provider latency and must not claim general search quality from a tiny
fixture set.

No Recall, MRR, nDCG, precision, or model-quality metric appears until a real
labelled relevance set exists in Phase 14.

## 12. Backend implementation

Planned modules:

- `app/relevance/mentor.py`: pure domain values, tokenizer, candidate grouping,
  feature calculation, banding, tie-breaking, claim audit, and quality summary;
- `app/core/config.py`: typed weights and validation;
- `app/services/mentor_discovery.py`: compose profile + paper discovery + pure
  candidate derivation and timing;
- `app/dependencies/mentor_discovery.py`: route composition with existing
  session, runtime, owner, profile, and paper boundaries;
- `app/schemas/mentor_discovery.py`: strict request/response contracts;
- `app/api/v1/routes/mentor_discovery.py`: thin transport;
- `scripts/evaluate_mentor_relevance.py`: deterministic fixture evaluation; and
- `reports/phase-07-relevance-baseline.json`: generated, reviewed baseline.

No new Python dependency is expected. Standard-library Unicode, dataclasses,
statistics, and monotonic timing are sufficient.

## 13. Frontend implementation

The `/mentors` page becomes a two-mode workspace:

### Live researcher evidence

- live mode is first and default;
- a focused query form supports text, DOI, and OpenAlex Work ID;
- `?query=` can prefill the page from live paper discovery without containing
  private data;
- TanStack Query mutation owns server state and aborts obsolete requests;
- runtime Zod validates the generated-client response;
- the candidate list shows relevance band, evidence confidence, paper count,
  current-role unknown, and availability unknown;
- desktop uses a sticky candidate list with a detailed evidence reader;
- mobile uses candidate list -> candidate detail -> back;
- detail shows every feature contribution, matched terms, source papers,
  paper-specific affiliations, warnings, policy version, and quality note;
- no live draft-generation button appears before Phase 8; and
- loading, empty, partial, error, and complete states are explicit.

### Recruiter demo

- existing fictional mentor, paper selection, deterministic draft, copy, save,
  and tracker behavior remains intact;
- `DemoNotice` appears only in demo mode;
- existing session state and E2E journey remain unchanged; and
- real and fictional contracts are never cast into one another.

### Discover-to-mentor transition

After live paper results, `/discover` adds a clear action linking to:

```text
/mentors?query=<encoded normalized query>
```

The mentors page prefills the query and lets the user explicitly start candidate
derivation. It does not silently call the provider merely because a URL opened.

## 14. Responsive and accessibility requirements

- semantic form, list, article, definition-list, and source-link structure;
- accessible live/demo tabs with arrow, Home, and End navigation;
- visible focus for all controls;
- list selection communicated with `aria-pressed` or the appropriate composite
  pattern;
- an explicit mobile back action that restores focus to the selected candidate;
- `aria-live` only for concise state changes, not the full evidence list;
- no horizontal document overflow at 360, 390, 768, or 1280px;
- usable at 200% zoom;
- reduced-motion support;
- restrained teal for evidence, indigo for policy/context, and amber only for
  uncertainty;
- no gauges, leaderboards, podiums, score rings, or decorative “AI” animation.

## 15. Test strategy

### Pure policy tests

- Unicode tokenization and stopword behavior;
- exact feature values and contribution arithmetic;
- weights sum and bounds validation;
- repeated author grouping and paper deduplication;
- no merging of distinct author IDs by display name;
- top-three evidence aggregation;
- recency boundaries and fixed evaluation year;
- completeness calculation;
- band thresholds and deterministic tie-breaking;
- profile fields that are intentionally ignored;
- title-only evidence limitations;
- evidence confidence;
- every factual explanation has evidence IDs; and
- unsupported-claim rate remains zero for generated templates.

### Service/API tests

- complete, partial, empty, provider error, and invalid-query outcomes;
- profile fallback and saved-profile changes influence only documented features;
- paper discovery is reused rather than duplicated;
- current title/institution/contact/availability remain unknown;
- historical affiliations remain attached to their papers;
- candidate and paper limits;
- stable request IDs and safe errors;
- source/cache metadata passes through;
- timing values are non-negative and bounded in shape;
- OpenAPI and generated client drift checks.

### Evaluation tests

- evaluator is deterministic for a fixed fixture and evaluation year;
- checked-in JSON matches regenerated output except documented timing tolerance;
- duplicate/evidence/unsupported-claim formulas are tested independently;
- the report labels fixture-only limitations.

### Frontend tests

- generated adapter request and runtime contract parsing;
- complete list/detail rendering;
- unknown role/institution/availability labels;
- contribution and supporting-paper evidence;
- loading, empty, partial, error, and retry;
- live/demo keyboard tabs;
- mobile list/detail focus restoration; and
- discover-to-mentor query prefill.

### E2E

- live papers -> mentor query transition -> candidate list -> evidence detail;
- repeated author is grouped into one candidate with two supporting papers;
- no professor/current-institution/availability claim appears;
- policy and contribution evidence is visible;
- recruiter demo outreach journey still passes;
- mobile list/detail and keyboard behavior;
- reduced motion and horizontal overflow;
- no OpenAlex key enters browser requests; and
- no automated request reaches the real OpenAlex service.

## 16. PostgreSQL and migration gate

No migration is planned, but PostgreSQL still receives a live integration gate:

1. upgrade a disposable database to Phase 6 head;
2. ingest representative OpenAlex works;
3. derive candidates through the Phase 7 endpoint;
4. repeat in a fresh application process;
5. confirm papers/authors/affiliations remain idempotent;
6. run `alembic check` and confirm no new operations; and
7. remove the disposable database and restore the prior container state.

If implementation reveals a real schema requirement, stop and update this plan
before creating a migration.

## 17. Dependencies

No new dependency is planned.

- Pydantic validates settings and contracts.
- SQLAlchemy supplies existing evidence reads/writes.
- Standard-library deterministic code handles tokenization, scoring, timing,
  and statistics.
- TanStack Query, React Hook Form, Zod, Lucide, and existing UI primitives cover
  the frontend.

Adding an NLP, fuzzy-match, vector, chart, or ranking library requires an
explicit measured need and a plan update.

## 18. Quality gates

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
npm.cmd audit --omit=dev --audit-level=high

docker compose --env-file .env.example config --quiet
git diff --check
```

Additional gates:

- disposable PostgreSQL 17 integration and zero-drift check;
- manual desktop, 390px, keyboard, focus, and 200% zoom browser QA;
- evidence-claim audit and checked-in quality baseline;
- secret/private-data scan; and
- full staged-diff review before commit.

## 19. Milestones

### A. Policy and domain

- [x] Add typed, validated `placement-relevance-v1` weights.
- [x] Add Unicode tokenizer and pure feature calculations.
- [x] Add candidate grouping, evidence bands, confidence, warnings, and
      deterministic tie-breaking.
- [x] Add structural claim-support audit and quality metrics.

### B. Service and API

- [x] Compose profile and paper discovery without duplicating retrieval.
- [x] Add mentor discovery request/response schemas.
- [x] Add the live route, structured errors, OpenAPI, and generated client.
- [x] Verify current title, institution, contact, and availability remain
      unknown.

### C. Frontend

- [x] Add live/demo mentor modes and query prefill.
- [x] Add accessible live query states and candidate list/detail.
- [x] Render contributions, source papers, historical affiliations, warnings,
      and policy metadata.
- [x] Preserve the fictional draft journey and add the live paper-to-mentor
      transition.

### D. Evaluation and verification

- [x] Add representative relevance fixtures and evaluator.
- [x] Check in the honest Phase 7 baseline report.
- [x] Pass backend, frontend, contract, E2E, PostgreSQL, browser, accessibility,
      supply-chain, and hygiene gates.
- [x] Update README, API README, ROADMAP, and learning log.
- [x] Review and commit Phase 7 as one unit.

## 20. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Paper author is presented as a professor | Use “researcher candidate”; keep academic title unknown unless separately verified. |
| Historical affiliation becomes a current-employer claim | Store/render it only on the supporting paper and keep current institution null. |
| Basic sorting is mistaken for AI ranking | Version and expose every feature; omit overall score; use evidence bands and explicit copy. |
| Lexical overlap overstates semantic fit | Show matched terms, call it observable text overlap, and defer embeddings/evaluation research. |
| Prolific authors dominate | Cap supporting-depth credit at three relevant papers and do not use global publication/citation counts. |
| Topic provider score is reused as student fit | Keep OpenAlex topic score as paper metadata only; relevance uses visible token overlap. |
| Recent paper is treated as higher quality | Label recency as activity evidence only and cap its weight. |
| Missing metadata unfairly becomes poor fit | Completeness affects evidence confidence, not an unsupported negative claim about the person. |
| Tiny fixture metrics look general | Label the report fixture-only and avoid ranking metrics without a labelled dataset. |
| Live provider instability breaks the interview | Preserve recruiter demo and run automated tests only against the owned provider stub. |
| Relevance logic becomes route/UI code | Keep a pure injected policy module with exact unit tests. |
| Profile data is mistaken for authenticated private data | Keep fictional-profile labels until Phase 10 and never log profile contents. |

## 21. Teaching targets

The Phase 7 learning-log entry must explain:

- candidate generation versus ranking;
- grouping authors across papers;
- why paper affiliation is not current employment;
- feature normalization, weights, contributions, and band thresholds;
- deterministic tie-breaking;
- lexical overlap and its limitations;
- evidence completeness versus evidence confidence;
- claim-to-evidence structural validation;
- request metrics versus offline evaluation metrics;
- why advanced ranking metrics require labelled relevance data;
- service composition and dependency inversion; and
- live server state versus fictional demo/session state.

## 22. Rollback

- Phase 6 remains recoverable as `795945f`.
- No schema migration is expected.
- The live mentor route and UI are additive; the existing deterministic demo
  remains intact.
- Evaluation uses repository fixtures and does not contact remote services.
- E2E owns its database, API, web process, and provider stub.
- No command may target an unknown developer database.

## 23. Completion rule

Phase 7 is complete only when candidates are derived exclusively from validated
supporting-paper authors, every ordering contribution is deterministic and
reviewable, unknown roles/current institutions/availability stay unknown,
historical affiliations retain their paper context, quality measurements are
honestly bounded, live and demo mentor experiences pass responsive and
accessibility gates, documentation teaches the full data flow, and the phase is
committed without advanced ranking or outreach generation.

The exact next step after acceptance is **Phase 8 — Evidence-grounded
outreach**: require human mentor and paper selection, then create an editable
versioned draft whose claims map only to verified profile facts and selected
publication evidence. The system still will not send email automatically.
