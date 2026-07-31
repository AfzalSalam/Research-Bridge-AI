# Research Bridge API

Minimal FastAPI foundation for Research Bridge AI. Run commands in this
directory so uv discovers `.python-version`, `pyproject.toml`, and `.env`.

```powershell
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
```

The only Phase 1 route is `GET /api/v1/health`.
