# Deployment & Incident Runbooks

This document outlines the operational procedures for deploying, maintaining, and recovering the Research Bridge AI stack.

## 1. Deployment Runbook

### Pre-Deployment Checklist
- [ ] Ensure CI/CD tests (`main.yml`) pass.
- [ ] Verify `docker-compose.yml` builds locally without errors.
- [ ] Check `.env` files for required secrets (`OPENAI_API_KEY`, `OPENALEX_API_KEY`, Supabase credentials).

### Deployment Steps
1. Pull the latest code on the production host.
2. Build and restart the containers:
   ```bash
   docker compose up --build -d
   ```
3. Database migrations run automatically during the `api` container startup (`uv run python -m alembic upgrade head`).
4. Run smoke tests:
   ```bash
   curl -f http://localhost:8000/api/v1/health || exit 1
   ```

---

## 2. Backup & Restore Runbook

### Backing up PostgreSQL
To create a daily backup of the database:
```bash
docker exec -t research-bridge-postgres-1 pg_dumpall -c -U postgres > dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql
```

### Restoring PostgreSQL
To restore from a backup file:
```bash
cat dump_file.sql | docker exec -i research-bridge-postgres-1 psql -U postgres
```

### Backing up Redis
Redis persistence is configured via standard AOF/RDB out of the box in the `redis:7-alpine` image, mapped to the `redis_data` volume. Back up the Docker volume directly if needed.

---

## 3. Incident Runbooks

### 3.1. API Container Crash Loop
**Symptom:** `docker ps` shows the `api` container continuously restarting.
**Cause:** Usually a database connection error, missing environment variable, or failed Alembic migration.
**Resolution:**
1. Check logs: `docker compose logs --tail=50 api`
2. If it's a migration error, downgrade or fix the schema locally:
   ```bash
   uv run alembic downgrade -1
   ```
3. If it's a connection error, ensure `postgres` and `redis` containers are healthy.

### 3.2. Rate Limits Exceeded (HTTP 429)
**Symptom:** Users report being blocked when creating outreach drafts.
**Cause:** A spike in traffic hitting the `fastapi-limiter` bounds.
**Resolution:**
1. Check Redis health: `docker compose exec redis redis-cli ping`
2. If a legitimate traffic spike, adjust the `times` and `seconds` parameters in `app.dependencies.rate_limiting`.
3. If abusive traffic, consider IP bans at the reverse proxy (Nginx/Cloudflare) layer.

### 3.3. External Provider Outage (OpenAlex / OpenAI)
**Symptom:** Discovery or Draft generation returns 502/503 or takes too long.
**Cause:** Upstream API is down.
**Resolution:**
1. The backend implements bounded retries and timeouts.
2. If OpenAI is down, the system gracefully falls back to deterministic templates.
3. If OpenAlex is down, discovery is unavailable. Post a status banner on the frontend until OpenAlex recovers.

---

## 4. Rollback Procedure

If a deployment introduces a critical regression:
1. Revert the main branch to the last known good commit.
2. If a database migration was applied and needs reverting:
   ```bash
   docker compose exec api uv run alembic downgrade -1
   ```
3. Re-deploy the stack:
   ```bash
   docker compose up --build -d
   ```
