# Research Bridge AI

![Hero image showing the application interface](/docs/images/hero.png)

Research Bridge AI is a full-stack academic discovery and research-opportunity platform. It helps students navigate the complex academic landscape by discovering relevant papers, identifying suitable professors with deterministic evidence, and generating editable, evidence-grounded outreach drafts.

This project enforces strict **evidence before generation**, ensuring that LLMs are only used for text composition based on deterministic facts, never for inventing scores or retrieving non-existent papers.

---

## Architecture

The project is structured as a modular monolith built with a **Next.js** frontend and a **FastAPI** backend, backed by **PostgreSQL** (with pgvector) and **Redis**.

```mermaid
graph TD
    User([User Browser]) --> NextJS[Next.js Frontend]
    NextJS --> FastAPI[FastAPI Backend]

    subgraph Data Layer
        FastAPI --> Postgres[(PostgreSQL)]
        FastAPI --> Redis[(Redis Cache)]
    end

    subgraph External APIs
        FastAPI --> OpenAlex[OpenAlex API]
        FastAPI --> LLM[OpenAI API]
        FastAPI --> Jobs[Greenhouse Job Boards]
    end

    classDef next fill:#000,stroke:#333,stroke-width:2px,color:#fff
    classDef fast fill:#009688,stroke:#333,stroke-width:2px,color:#fff
    classDef db fill:#336699,stroke:#333,stroke-width:2px,color:#fff
    
    class NextJS next
    class FastAPI fast
    class Postgres,Redis db
```

### Tech Stack

- **Frontend**: Next.js 14 App Router, React, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, React Hook Form, Zod.
- **Backend**: Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, HTTPX, LangGraph.
- **Infrastructure**: Docker, PostgreSQL (pgvector), Redis.
- **Testing/Quality**: Playwright, Pytest, Ruff, Mypy, ESLint, axe-core.

---

## Core Features

- **Profile & Preference Tracking**: Persist research interests, past projects, and location preferences to surface the most relevant matches.
- **Deterministic Academic Discovery**: Query the OpenAlex API to find exact paper authors, normalized institutions, and verifiable topics.
- **Evidence-Grounded Recommendations**: Professor candidates are ranked based on a verifiable multi-factor heuristic (query evidence, profile alignment, supporting depth, recent activity), not LLM hallucination.
- **Safe Outreach Drafting**: Select specific papers and generate an outreach draft. The system maps generated claims to explicit source evidence, warning the user of any unsupported claims.
- **Verified Opportunities**: Aggregate academic opportunities directly from known greenhouse boards using an explicit allowlist to prevent SSRF and hallucination.
- **LangGraph Workflow Orchestration**: Complex multi-step reasoning is handled asynchronously with streaming updates, preserving the deterministic nature of intermediate steps.

---

## Local Development & Docker Deployment

Research Bridge AI supports a full local-production setup using Docker Compose.

### Requirements

- Docker Desktop (or equivalent engine)
- Node.js 20+ (for local frontend development)
- `uv` (for local backend development)

### Running with Docker Compose (Production Preview)

1. Clone the repository.
2. Copy the example environment files:
   ```bash
   cp apps/web/.env.example apps/web/.env.local
   cp apps/api/.env.example apps/api/.env
   ```
3. Boot the stack:
   ```bash
   docker compose up --build -d
   ```
4. Access the frontend at `http://localhost:3000` and the API documentation at `http://localhost:8000/docs`.

### Running Locally (Development)

**Backend:**
```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd apps/web
npm ci
npm run dev
```

---

## Documentation & Runbooks

- [Architecture & Rules](AGENTS.md)
- [Product Specification](PROJECT_SPEC.md)
- [Deployment & Incident Runbooks](docs/deployment.md)
- [Recruiter Interview Script](docs/recruiter-interview-script.md)
- [Learning & Development Log](docs/LEARNING_LOG.md)

## Limitations

- **Search Capabilities**: OpenSearch integration is deferred. PostgreSQL `tsvector` is used for basic full-text needs.
- **Email Delivery**: The platform explicitly does **not** send emails automatically. It only generates drafts for human review.
- **Data Completeness**: Job titles, contact addresses, and current funding status remain unknown if not explicitly verified by a supported API. The system prefers showing "Unclear" over guessing.

## License

Copyright 2026. All rights reserved.
