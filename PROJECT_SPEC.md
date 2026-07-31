# PROJECT_SPEC.md

## Product

**Research Bridge AI** is an evidence-first academic discovery and research-
opportunity platform for bachelor’s and master’s STEM students.

It helps a student turn a broad research interest into a reviewable path:
relevant papers, plausible mentors, the evidence behind each suggestion,
verified opportunities, a personalized outreach draft, and an application
record.

The placement release is also a portfolio-quality full-stack and AI system. It
must demonstrate real engineering depth without presenting experimental or
unsupported behavior as production intelligence.

## Product principles

1. Evidence before generation.
2. Academic APIs before controlled extraction.
3. Deterministic retrieval, validation, and relevance before LLM explanation.
4. Unknown availability, funding, work mode, and contact data remain unknown.
5. Human selection and review before an outreach draft is used.
6. No automatic or mass email sending.
7. Accessible, professional interfaces over decorative “AI” effects.
8. Measured system quality over impressive-sounding agent labels.

## Primary user

A bachelor’s or master’s STEM student who knows a research topic or method but
does not yet know which papers, researchers, or legitimate opportunities to
investigate.

The first UI language is English. Names, institutions, locations, identifiers,
and publication metadata must preserve international characters correctly.

## Placement-release journeys

### Professor discovery

1. The student creates a structured profile containing degree, graduation
   year, interests, skills, methods, and optional research/project experience.
2. The student enters a topic, method, keyword set, DOI, or paper identifier.
3. The student may add location and institution preferences. Funding and work
   mode apply to opportunities, not as unsupported professor attributes.
4. The system retrieves papers through OpenAlex first.
5. Deterministic services normalize and deduplicate papers, preserve external
   identifiers and provenance, and resolve authors and institutions.
6. The system derives plausible mentor candidates from paper authors and
   verified academic roles where available.
7. A transparent basic relevance heuristic orders the candidates using
   supporting-paper topic relevance, recent relevant publication activity, and
   evidence completeness. It is not called a research-grade ranking model.
8. The student sees the supporting papers, source links, evidence strength,
   feature contribution, and explicit uncertainty for each candidate.
9. The student selects a mentor and the specific paper evidence to use.
10. The system produces an editable outreach draft grounded only in verified
    student facts and selected publication evidence.
11. The student reviews, edits, copies, saves, or tracks the draft. The system
    never sends it automatically.

### Evidence-grounded outreach

The outreach workflow is a core differentiator, not a generic email generator.

- Generation happens only after the student selects a mentor.
- The draft should refer to one or two selected papers using verified title,
  year, venue, topic, and source metadata.
- Claims about a paper’s method or result require available source text or a
  validated abstract; title-only evidence must not be expanded into invented
  technical details.
- Student claims come only from the saved profile or explicit draft input.
- Availability is phrased as a respectful question unless an official source
  confirms it and supplies a last-verified timestamp.
- Contact details are never guessed.
- The UI shows claim-to-evidence references and uncertainty warnings.
- A deterministic fallback template remains available when an LLM is disabled,
  invalid, or unavailable.
- Every generated draft remains editable and versioned.

### Research internships and opportunities

1. The student searches by topic and preferences.
2. The system returns records from official or controlled allowlisted sources.
3. The student filters by country, work mode, funding, field, and deadline.
4. Unknown values remain `Unclear` rather than being inferred.
5. Every record shows its source and last-verified time.
6. The student saves the opportunity or tracks an application and follow-up.

### Demo mode

- The deployed application includes a deterministic, clearly labelled demo
  journey that does not depend on academic APIs or an LLM being available.
- Demo people, institutions, contact information, and outcomes must be visibly
  fictional.
- Demo mode exercises the same typed UI contracts as live mode so it remains a
  useful end-to-end demonstration rather than a separate static mock-up.

## Placement-release scope

- Next.js App Router frontend with strict TypeScript.
- FastAPI backend with typed versioned contracts.
- PostgreSQL data model and Alembic migrations.
- Structured student profile.
- Real OpenAlex paper retrieval with normalization, provenance, bounded retry,
  rate-limit handling, and partial-failure states.
- Professor candidates derived from paper authors.
- Basic deterministic relevance heuristic with visible evidence contribution.
- Mentor master-detail evidence experience.
- Editable, evidence-grounded custom outreach draft.
- Verified-opportunity model, saved items, and application tracker.
- Authentication, user isolation, and private profile/resume handling before
  public deployment.
- LangGraph orchestration only after deterministic services work, with progress
  reporting and human-review checkpoints.
- Accessibility, responsive design, automated tests, observability, deployment,
  demo data, architecture documentation, and an interview demo script.

## Post-placement advanced scope

- PostgreSQL full-text and pgvector retrieval experiments beyond core need.
- Embedding evaluation and weight tuning.
- Cross-encoder reranking.
- Labelled relevance datasets.
- Recall@5, Recall@10, MRR, and nDCG@10 ranking experiments.
- Larger-scale multi-source enrichment and identity reconciliation.
- Background metadata refresh and cache infrastructure based on measured load.
- Retrieval-evaluation dashboard and deeper prompt tracing.

These features may be prepared for architecturally, but they must not delay or
be falsely claimed by the placement release.

## Non-goals

- Automatic or mass emailing.
- Guaranteed professor availability, response, funding, acceptance, or work
  mode.
- Estimated response rates without consented and statistically meaningful data.
- Prestige-based defaults such as an undefined “Top 100” institution filter.
- Scraping Google Scholar, private pages, restricted information, or sites that
  prohibit extraction.
- Guessing academic titles, contact details, mentoring history, or opportunity
  attributes.
- Letting an LLM retrieve records, write database state, determine numeric
  relevance, or bypass permissions.
- Microservices, CrewAI, AutoGen, OpenSearch, Celery, or Redis before measured
  product need.

## Required result contracts

### Professor result

- verified display name;
- verified academic title or `Unknown`;
- institution and location with source provenance;
- research topics derived from supporting publications;
- supporting papers with external IDs, year, venue, and source URLs;
- placement-release relevance band and deterministic feature contribution;
- evidence completeness and confidence;
- availability status with `Unknown` as the default;
- warnings for unsupported or stale facts;
- source and last-verified metadata where applicable;
- editable draft action only after selection.

### Outreach draft

- recipient display name and verified contact or `Unknown`;
- subject;
- editable body;
- selected student facts;
- selected supporting papers;
- claim-to-evidence references;
- uncertainty warnings;
- generation mode (`llm` or deterministic fallback);
- provider/model metadata when applicable;
- prompt version and draft version;
- created and updated timestamps.

### Internship result

- title;
- organization;
- field;
- country;
- work mode including `Unclear`;
- funding including `Unclear`;
- duration;
- eligibility;
- deadline and stale/expired state;
- official application link;
- source URL;
- last-verified timestamp;
- evidence confidence.

## Design direction

The approved Figma Make prototype defines the visual direction, not the code
architecture.

- Premium editorial-academic aesthetic.
- Warm neutral canvas with restrained teal and indigo brand accents.
- Warm amber only for uncertainty or pending verification.
- Serif display typography paired with a highly readable UI sans serif.
- Hairline dividers, generous whitespace, flat scannable lists, and limited
  shadows or decorative cards.
- Desktop mentor master-detail workspace.
- Mobile task sequence: results list -> mentor detail -> draft.
- Writer-focused draft editor with evidence and verification assistance.
- Meaningful loading stages, never fabricated progress percentages.

Every data screen requires loading, empty, error, and partial-failure states.
Every interactive flow requires keyboard access, visible focus, accessible
labels, responsive behavior, 200% zoom support, and reduced-motion support.

## Success criteria

The placement release is successful when:

- a recruiter can run or open the project and complete the demo journey;
- the student can explain the architecture and data flow end to end;
- live paper results retain source provenance and failure information;
- the application never turns unknown evidence into a confident claim;
- the email draft visibly connects its customized content to selected evidence;
- critical frontend, backend, contract, database, and E2E checks pass;
- the deployed system has a runbook, architecture diagram, limitations, and
  honest quality measurements.
