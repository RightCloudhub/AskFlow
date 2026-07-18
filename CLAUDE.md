# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

AskFlow is a single-tenant, self-hostable enterprise customer-service system (RAG + Agent). Backend is FastAPI (`apps/api`), frontend is React + Vite (`apps/web`). Most docs and PRD references are in Chinese; code comments cite PRD sections like `(PRD §4.2)` as anchors into `docs/prd/PRD.md`.

## Commands

All backend commands run from `apps/api` unless noted. Tests/eval need no LLM, DB server, or secrets — the stack is offline-first (see Architecture).

```bash
# Backend dev server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ".[dev]"
export ASKFLOW_ENV=development SECRET_KEY=dev-secret-change-me
export DATABASE_URL=sqlite+aiosqlite:///./askflow.dev.db   # or postgresql+asyncpg://...
uvicorn app.main:app --reload --port 8000                  # docs at /docs, health at /health

# Tests (conftest auto-sets ASKFLOW_ENV=test, in-memory SQLite, ASKFLOW_PROFILE=full)
pytest -q                                                  # full suite
pytest tests/unit/test_intent.py -q                        # one file
pytest tests/unit/test_intent.py::test_name -q             # one test
pytest tests/unit tests/integration -q                     # by layer (unit / integration / e2e)

# Offline eval (from REPO ROOT — golden answers + refusal cases)
PYTHONPATH=apps/api python evals/runners/run_eval.py

# Frontend (from apps/web)
npm install && npm run dev                                 # :5173, proxies /api,/ws,/health → :8000
npm run build                                              # tsc --noEmit + vite build

# Lint + hard metric gate (from repo root)
ruff check apps/api                                        # line-length 100, py311
python3 scripts/ops/check_code_metrics.py                  # exit 1 on any violation
```

Optional infra (Postgres/Redis/MinIO): `docker compose -f infra/compose/dev/docker-compose.yml up -d`.

## Architecture

### Plugin/profile system — read this first

The API router is **assembled at startup by plugins**, not declared statically. Nothing is wired until plugins register. To understand or change how any route/handler exists, start here:

- `packages/contracts/features.yaml` — defines **profiles** (`full`, `enterprise`, `mvp`, `core-only`, `faq-only`) as plugin lists, plus each plugin's `depends` graph.
- `ASKFLOW_PROFILE` selects a profile; `ASKFLOW_FEATURES=+sla,-mcp` applies comma-separated deltas on top.
- `app/plugins/loader.py` → `resolve_features()` (profile + deltas + dependency closure) → `topological_order()` → instantiates builtins from `app/plugins/builtin/*.py` (one file per plugin: `core`, `rag`, `agent`, `tools`, `ticket`, `handoff`, `knowledge`, `ops`, `cost`, `sla`, `notify`, `sso`, `teams`, `connectors`, `launch`, `analytics`, `mcp`, `widget`, `feishu`, `qc`).
- Each plugin's `register(ctx)` populates an `AppContext` (`app/plugins/context.py`): API/admin routers, **route handlers**, **side-effect handlers**, admin nav. `AppContext` is a process-wide singleton in `app/plugins/runtime.py`.

Adding a capability usually means: add/extend a builtin plugin, wire it into `features.yaml` (with `depends`), and register routers/handlers on `ctx`.

### Agent pipeline (single message → answer)

`app/services/agent/pipeline/runner.py` (`MessagePipeline.handle`) orchestrates one turn:

1. **Harness.prepare** (`harness/policy.py`) — hard input guards: empty / too-long / prompt-injection. **Security copy and thresholds are code constants here, never prompt templates** — preserve that invariant.
2. **IntentClassifier** (`intent/`) → **RouteResolver** (`router/`) picks one of the legal routes.
3. **Table-driven dispatch** to a route handler (`clarify`, `refuse`, `rag`, `tool`, `ticket`, `handoff`), resolved from `AppContext.route_handlers` (falls back to `pipeline/defaults.py` when no context is loaded, e.g. bare unit tests).
4. **Harness.finalize** — output guards (empty-output message, truncation).

Supporting pieces: `LoopEngine` (`loop/`, bounded tool-calling agent loop), `ModelRouter` (`model_router/`, purpose→model with a fallback chain and a `force_primary_fail` test hook), `CostLedger` (`cost/`), `SlotTracker` (`slots/`). All budgets (loop steps, tool calls, wall-ms, retries, thresholds) live as named fields in `Settings` — never inline magic numbers.

**Side effects** (create ticket, enqueue handoff, log knowledge gap, record cost) run *after* the pipeline via `SideEffectHandler`s registered on the context — see `app/services/chat/side_effects/`.

### Honest RAG

`app/services/rag/pipeline.py`: QueryRewriter (rule-based synonyms by default, LLM optional/fallback) → BM25 + vector search → RRF fusion → **GroundingEvaluator** → ContextAssembler → AnswerGenerator → citation verification. **Refusal is first-class**: if evidence is below the grounding threshold, it returns a refused result with a reason instead of answering. Grounding thresholds are `Settings` constants (`grounding_threshold`, `grounding_min_hits`, `grounding_weak_sources`).

### Offline-first LLM

The whole system runs with **no LLM configured** — this is why tests and eval need no API key. `AnswerGenerator` does extractive synthesis when no LLM is present; classifier/rewriter degrade to rules. A real OpenAI-compatible LLM is opt-in via env (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL_*`, `EMBEDDING_*`). When adding LLM-backed features, keep a deterministic offline path.

### Config, fail-safe, and data

- `app/core/config.py` — `Settings` (pydantic-settings, `@lru_cache`d). `assert_startup_safe()` **refuses to boot** with a weak/short `SECRET_KEY` or `OIDC_MOCK=1` when `ASKFLOW_ENV` is staging/production (S-01). `is_production_like` hides `/docs`. Registration/bootstrap-admin are gated by `local_register_allowed()` / `bootstrap_admin_allowed()`.
- `app/core/database.py` — SQLAlchemy 2 async; `init_db()` creates tables for dev/test convenience, **production uses Alembic** (`alembic/versions/`). SQLite default, Postgres via asyncpg.
- Middleware order matters (Starlette: last added = outermost) — see `create_app()` in `app/main.py`. Background SLA/handoff sweeper (`app/workers/enterprise_jobs.py`) is gated by `sweeper_enabled` and disabled in tests.

### Testing gotcha: cached singletons

`get_settings()` is `@lru_cache`d and `AppContext` is a global. Tests that change env or profile **must** call `get_settings.cache_clear()` and `set_app_context(None)` (see `tests/conftest.py`, which also swaps `database.engine`/`SessionLocal` to a per-test in-memory SQLite and overrides `get_db`). Follow that pattern in new tests and scripts.

## Conventions

- **Hard code metrics are enforced** (`AGENTS.md`, `docs/engineering/code-metrics.md`, checked by `scripts/ops/check_code_metrics.py`): functions ≤ 50 non-blank lines, files ≤ 300 lines, nesting ≤ 3, positional params ≤ 3 (use a dataclass/TypedDict beyond that), cyclomatic complexity ≤ 10, **no magic numbers** (extract named constants or `Settings` fields). New/modified code must comply; touching an over-limit file means converging it toward compliance in the same change. Exceptions are listed in `code-metrics.md` §3.
- Prefer guard clauses and table/dict dispatch over deep `if/elif` chains (keeps nesting and complexity within limits).
- Commits follow conventional style with a scope, matching history: `fix(cost): ...`, `feat(audit): ...`, `docs: ...`.
- Key docs: `docs/STATUS.md` (completion matrix), `docs/prd/STRUCTURE.md` (directory ↔ PRD map), `docs/contracts/agent-behavior.md` (agent behavior contract), `docs/architecture/` (context engineering, query rewrite, RAG, agent pipeline, the three pillars).
