# PROJECT_SPEC.md

## Product

**Research Bridge AI** — an AI-assisted academic discovery and research-internship platform.

## Main user journey: professor discovery

1. User creates an academic profile.
2. User enters a research interest.
3. User selects country, work-mode, and funding preferences.
4. System retrieves and normalizes relevant papers.
5. System resolves authors, institutions, and professor candidates.
6. System ranks candidates with deterministic and semantic features.
7. User sees score breakdown, evidence, sources, confidence, and uncertainty.
8. User selects a professor.
9. System generates an editable evidence-grounded email draft.
10. User saves the match, draft, or application.

## Main user journey: internships

1. User enters topic and preferences.
2. System retrieves verified opportunities.
3. User filters by country, work mode, funding, field, and deadline.
4. Every opportunity shows source and last-verified date.
5. User saves it or tracks an application.

## MVP

- Next.js TypeScript frontend.
- FastAPI backend.
- Student profile.
- Real paper retrieval through OpenAlex.
- Professor candidates derived from paper authors.
- Basic hybrid ranking with score breakdown.
- Evidence panel for each recommendation.
- Editable grounded email draft.
- Verified internship listing model.
- Saved items and application tracker.
- Automated tests and deployment.

## Advanced version

- PostgreSQL full-text search + pgvector.
- Cross-encoder reranking.
- LangGraph workflow with progress streaming.
- Multiple academic-source enrichment.
- Authentication and private resume storage.
- Background metadata refresh.
- Retrieval evaluation dashboard.
- Observability and prompt tracing.

## Non-goals

- Automatic mass emailing.
- Guaranteeing professor availability.
- Claiming paid/remote/open positions without evidence.
- Scraping private or restricted information.
- Letting an LLM create ranking scores without measurable features.

## Result requirements

Professor result:

- name;
- institution;
- research areas;
- supporting papers;
- source URLs;
- match score and feature breakdown;
- evidence confidence;
- uncertainty warnings;
- editable draft after selection.

Internship result:

- title;
- organization;
- field;
- country;
- work mode;
- funding including `unclear`;
- duration;
- eligibility;
- deadline;
- official/source link;
- last verified date.
