# Phase 13 — Deployment and Portfolio Release

This plan outlines the final pre-release hardening, deployment configuration, and portfolio presentation tasks for Research Bridge AI.

## Goal Description
Deploy Next.js, FastAPI, PostgreSQL, and Redis with CI/CD, migrations, health checks, rate limiting, and rollback runbooks. Polish the README, add architecture diagrams, and create a demo script for recruiters.

## Proposed Changes

### 1. CI/CD & Automation
#### [NEW] `.github/workflows/main.yml`
- Linting, typechecking, and E2E testing for the web frontend.
- Ruff checking, mypy typechecking, and pytest for the API backend.

### 2. Dockerization & Deployment
#### [NEW] `apps/web/Dockerfile`
- Multi-stage build for Next.js standalone output.
#### [NEW] `apps/api/Dockerfile`
- Multi-stage build for FastAPI using `uv`.
#### [NEW] `docker-compose.yml`
- Full stack orchestration (PostgreSQL, Redis, API, Web) for staging/production preview.

### 3. Production Hardening (Redis & Rate Limiting)
#### [MODIFY] `apps/api/pyproject.toml`
- Add `redis` and `fastapi-limiter` dependencies.
#### [MODIFY] `apps/api/app/main.py`
- Configure Redis connection pool on app startup.
- Add FastAPI rate limiter dependency.

### 4. Documentation & Runbooks
#### [MODIFY] `README.md`
- Comprehensive rewrite with architecture diagrams (Mermaid), screenshots, tech stack, and local development guide.
#### [NEW] `docs/deployment.md`
- Runbooks for deployment, migrations, backups, and rollbacks.
#### [NEW] `docs/recruiter-interview-script.md`
- A 5-minute walkthrough script demonstrating the deterministic placement flow.

## Verification Plan
### Automated Tests
- `npm run test:e2e` and `pytest` still pass.
### Manual Verification
- `docker-compose up --build` successfully launches the stack.
- Rate limits correctly return HTTP 429 Too Many Requests when exceeded.
