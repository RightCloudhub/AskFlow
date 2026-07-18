# Runbook: Multi-worker cancel · metrics · index invalidation (PRD E12)

## Cancel

| Client frame | Effect |
|--------------|--------|
| `{"type":"cancel","conversation_id":"<id>"}` | Sets cancel flag for conversation |
| optional `run_id` | Also flags that run |

Backend:

- `app/services/cancel_registry.py` — process dict + optional Redis (`REDIS_URL`, key `askflow:cancel:{id}`, TTL `CANCEL_TTL_SECONDS`).
- Chat pipeline passes `cancel_key=conversation_id` into RAG generator.
- Mid-stream LLM tokens stop when flag is set; offline path short-circuits to `生成已取消。`.
- Metrics: `askflow_cancel_requests_total{scope}`, `askflow_cancel_honored_total`.

**Multi-worker:** all API workers must share the same Redis for cross-instance cancel; without Redis, cancel is single-process only.

## Metrics

- Scrape **each** worker `/metrics` (or use Prometheus multi-target).
- Core labels: HTTP, RAG refusal, handoff timeout, LLM error/fallback, embedding, index jobs, cancel.
- Admin analytics aggregates DB-backed signals; Prometheus is the per-process source of truth.

## Index invalidation

| Event | Behavior |
|-------|----------|
| Reindex | CAS `pending/active/failed → indexing`; write-new-then-delete BM25; vector `delete_document` + upsert; bump `generation`; save revision |
| Delete | Remove BM25 rows for doc_id + vector delete + DB row |
| Worker crash mid-index | Status may stay `indexing`; reindex again after CAS allows (status not in claim set until failed/manual) |

Generation monotony prevents serving mixed old/new chunks for the same doc once reindex completes.

## Verify

```bash
PYTHONPATH=. pytest tests/unit/test_prd_wave_gaps.py tests/integration/test_multi_worker_safety.py -q
```
