# AskFlow API

FastAPI backend for AskFlow. The [PRD v1.3](../../docs/prd/PRD.md) defines the enterprise baseline; the [customer service Agent proposal](../../docs/prd/customer-service-agent.md) describes the newer goal-based runtime and its remaining acceptance work.

For beginner-oriented setup, environment-file instructions, all current settings, and connection walkthroughs, see the [configuration guide](../../docs/configuration/README.md).

## Quick start

```bash
# From the repository root
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# SQLite-backed local run
export ASKFLOW_ENV=development
export DATABASE_URL=sqlite+aiosqlite:///./askflow.dev.db
export SECRET_KEY=dev-secret-change-me
export ASKFLOW_PROFILE=full
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs (disabled in staging/production). Health: http://localhost:8000/health.

For PostgreSQL, Redis and MinIO, start dependencies from the repository root:

```bash
docker compose -f infra/compose/dev/docker-compose.yml up -d
cd apps/api
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow
export REDIS_URL=redis://localhost:6379/0
export ASKFLOW_ENV=development
export SECRET_KEY=dev-secret-change-me
uvicorn app.main:app --reload --port 8000
```

## Service tasks and order connector

Chat intake creates a durable task and dispatch row in the same transaction as the messages. The API starts a database-backed worker when the Agent plugin and service tasks are enabled, except in `ASKFLOW_ENV=test`. Redis is not required for this scheduler.

| Variable | Default | Behavior |
|---|---|---|
| `SERVICE_TASKS_ENABLED` | `true` | Enables chat task intake and the background worker |
| `SERVICE_TASKS_GOALS` | `order_status` | Comma-separated intake allowlist; also supports `ticket_resolution,human_handoff` |
| `SERVICE_TASK_POLL_SECONDS` | `5` | Worker scan interval in seconds; minimum 1 |
| `ORDER_LOOKUP_URL` | Empty | HTTP GET endpoint for authenticated order queries |
| `ORDER_LOOKUP_TOKEN` | Empty | Optional bearer token sent to that endpoint |

The aliases `order`, `ticket` and `handoff` map to their corresponding goal names. An empty goal allowlist leaves new chat messages on the existing pipeline. Removing a goal does not stop already queued tasks; disabling `SERVICE_TASKS_ENABLED` and restarting the API stops its scheduler as well. Neither change reverses an operation already sent.

The scoped order adapter sends `order_id` and the authenticated `customer_id` as query parameters. It expects a flat JSON response such as:

```json
{"order_id": "ORD202401019999", "customer_id": "<authenticated-user-id>", "status": "shipped"}
```

The service verifies both IDs and requires a concrete status. Missing configuration, mismatched ownership and mock results do not resolve the task. This scoped response contract differs from the older synchronous order tool. It currently uses a fixed five-second HTTP timeout.

Completed or waiting tasks can append one deduplicated assistant update to an active conversation. Read the conversation messages again to see that update; the worker does not broadcast a new WebSocket frame.

Ticket intake is opt-in and confirms ticket registration, not resolution of the reported problem. Handoff intake is also opt-in: enqueueing alone does not prove acceptance, and there is no automatic claim-event subscription. Notification and refund adapters require host-supplied connectors and are absent from the default policy registry; adding `notify` or `refund` to the allowlist does not wire them into chat.

See [runtime and recovery](../../docs/architecture/customer-service-runtime.md), [lifecycle](../../docs/architecture/customer-service-lifecycle.md) and [conformance boundaries](../../docs/architecture/agent-conformance.md).

## Authenticated task and memory APIs

All paths below have the `/api/v1` prefix and are mounted by the Agent plugin. They use the authenticated user's scope; guest tokens cannot call them.

| Method and path | Purpose |
|---|---|
| `GET /agent/tasks?limit=20&after=UUID` | List the customer's tasks with a cursor |
| `GET /agent/tasks/{task_id}` | Read the public task summary |
| `POST /agent/tasks/{task_id}/cancel` | Cancel with `expected_version` and `reason` |
| `POST /admin/service-tasks/{task_id}/accept-handoff` | Agent/admin takeover using `expected_version` and their claimed `handoff_id` |
| `GET /agent/preferences` | Read the customer's preferences |
| `PUT /agent/preferences` | Confirm/create/correct a preference with optimistic versioning |
| `DELETE /agent/preferences/{key}?expected_version=N` | Delete a preference value |

Task responses exclude operation arguments, receipts and internal diagnostics. See [task request examples and conflicts](../../docs/architecture/customer-service-lifecycle.md) and [preference keys, consent and retention](../../docs/architecture/customer-preference-memory.md). Facts, event timelines and experience stores currently have Python interfaces only.

## Plugin discovery

`GET /api/v1/admin/features` requires an agent/admin account and returns the current profile, enabled/loaded plugins, dependency catalog, available profiles, feature deltas, route handlers, side effects and Admin navigation. The web UI displays this at `/admin/plugins`.

Set `ASKFLOW_PROFILE` and optional `ASKFLOW_FEATURES` before starting the API. The page and endpoint are read-only; changes require an API restart. Profiles and dependencies are defined in [features.yaml](../../packages/contracts/features.yaml); see [plugin architecture](../../docs/architecture/plugins.md).

## Database upgrades

The latest five commits introduce this migration chain:

| Revision | Adds |
|---|---|
| `20261003_service_tasks` | Versioned `service_tasks` checkpoints |
| `20261003_customer_preferences` | `customer_preferences` |
| `20261003_service_dispatches` | Durable `service_dispatches` leases |
| `20261004_agent_memories_locks` | `agent_memories` and `service_object_locks` |

For an existing deployment managed by Alembic, set its `DATABASE_URL` and run before starting the updated API:

```bash
# From apps/api, using its activated virtual environment
python -m alembic current
python -m alembic upgrade head
```

These migrations add the service-task tables alongside existing business tables; they are not a complete initial application schema. Startup currently calls `init_db/create_all` to create missing ORM tables, including these new ones, but does not update Alembic's revision record.

Do not blindly run the create-table migrations over tables already created by `create_all`. For a disposable local database, use a new SQLite file. For a retained database, compare its schema with the migrations and reconcile its Alembic revision before upgrading; stamp only a revision whose schema is already present. Task budget fields live in checkpoint JSON and have defaults for older records.

## Verification

```bash
# From apps/api with the virtual environment active
python -m pytest -q
ruff check .
PYTHONPATH=. python ../../evals/runners/run_eval.py
```

Focused coverage for the latest changes:

```bash
python -m pytest -q \
  tests/unit/test_service_*.py tests/unit/test_intake_*.py \
  tests/unit/test_domains_*.py tests/unit/test_memory_*.py \
  tests/unit/test_customer_memory.py tests/unit/test_features_discovery.py \
  tests/unit/test_plugins_*.py tests/integration/test_agent_conformance.py \
  tests/integration/test_chat_service_tasks.py \
  tests/integration/test_customer_memory_api.py \
  tests/integration/test_service_tasks_api.py
```

Tests drive `app.workers.service_tasks.run_once()` explicitly because background loops are disabled in test mode. Recorded results and production validation limits are in [STATUS](../../docs/STATUS.md).

## Key modules

| Path | Responsibility |
|---|---|
| `app/core/` | Configuration, database, authentication dependencies |
| `app/plugins/discovery.py` | Read-only runtime capability view |
| `app/services/agent/intake/` | Conservative goal intake and atomic task creation |
| `app/services/agent/service/` | Checkpoints, execution, recovery, selection, budgets, locks, dispatch and control |
| `app/services/agent/domains/` | Order, ticket, handoff, notification and refund adapters |
| `app/services/agent/memory/` | Preferences, verified facts, event references and experience hints |
| `app/services/chat/session/turn.py` | Chat intake, pipeline fallback and message persistence |
| `app/workers/service_tasks.py` | Database lease claims and goal policy dispatch |
| `app/services/rag/` | Honest RAG |
| `app/api/v1/agent/` | Classification, customer task and preference APIs |
