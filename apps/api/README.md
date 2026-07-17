# AskFlow API

FastAPI backend for AskFlow (PRD v1.1).

## Quick start

```bash
# from repo root
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# SQLite-backed local run (no external deps)
export ASKFLOW_ENV=development
export DATABASE_URL=sqlite+aiosqlite:///./askflow.dev.db
export SECRET_KEY=dev-secret-change-me
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

With Docker Compose (Postgres + Redis + MinIO):

```bash
# from repo root
docker compose -f infra/compose/dev/docker-compose.yml up -d
export DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow
export REDIS_URL=redis://localhost:6379/0
export ASKFLOW_ENV=development
export SECRET_KEY=dev-secret-change-me
uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
cd apps/api && pytest -q
```

## Key modules

| Path | PRD |
|------|-----|
| `app/core/` | config, DB, fail-safe (S-01) |
| `app/services/auth/` | §4.1 JWT / RBAC |
| `app/services/agent/` | §4.3 Harness · Intent · Router · Pipeline |
| `app/services/rag/` | §4.2 Honest RAG |
| `app/api/v1/` | §7.1 REST |
