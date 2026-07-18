# Runbook: Reindex · Model rotation · Three-store reconciliation (PRD E15)

## 1. Document reindex

### Single document (sync)

```bash
# Admin JWT required
curl -sS -X POST "$API/api/v1/embedding/reindex/$DOCUMENT_ID" \
  -H "Authorization: Bearer $TOKEN"
```

### Async queue (`INDEX_ASYNC=1`)

1. Upload or reindex enqueues `askflow:index_jobs` (Redis if `REDIS_URL`, else in-process).
2. API process runs `index_worker` consumer (lifespan) → `chunk → embed → BM25 + vector upsert` + revision snapshot under `REVISION_STORE_DIR`.
3. Poll document status: `GET /api/v1/admin/documents` until `status=active`.

### Full reindex after embedding model change

1. Set `EMBEDDING_MODEL` / `EMBEDDING_DIM` (or OpenAI-compatible URLs).
2. Restart API (clears process-local memory vector index).
3. For each active document, call reindex (script loop or Admin UI).
4. If using Chroma (`CHROMA_HOST` or `CHROMA_PERSIST_DIR`), drop or recreate collection when **dimension** changes:

```bash
# Optional: wipe local chroma volume then restart compose
docker compose -f infra/compose/dev/docker-compose.yml restart chroma
```

### Generation rollback / diff (E10)

```bash
# List generations
curl -sS "$API/api/v1/admin/documents/$DOCUMENT_ID/generations" -H "Authorization: Bearer $TOKEN"

# Diff two generations
curl -sS "$API/api/v1/admin/documents/$DOCUMENT_ID/diff?from_generation=1&to_generation=2" \
  -H "Authorization: Bearer $TOKEN"

# Rollback body to generation N (creates a new generation from snapshot)
curl -sS -X POST "$API/api/v1/admin/documents/$DOCUMENT_ID/rollback?target_generation=1" \
  -H "Authorization: Bearer $TOKEN"
```

Snapshots live under `REVISION_STORE_DIR` (default `./data/revisions`).

---

## 2. Model rotation

| Purpose | Env |
|---------|-----|
| classify | `LLM_MODEL_CLASSIFY` |
| rewrite | `LLM_MODEL_REWRITE` |
| generate | `LLM_MODEL_GENERATE` |
| summary | `LLM_MODEL_SUMMARY` |
| embedding | `EMBEDDING_MODEL` |

1. Create a **Launch Card** for the change (`/admin/launch-cards`) with expected metrics.
2. Deploy new env vars; restart API workers **rolling** so ModelRouter picks new models.
3. Fallback chain is automatic (`ModelRouter.call_with_fallback`); watch:
   - `askflow_llm_fallback_total`
   - `askflow_llm_error_total`
   - Admin `/admin/costs/summary`
4. After soak, fill Launch Card measured metrics; rollback env if quality/cost regresses.
5. Offline regression: `PYTHONPATH=apps/api python evals/runners/run_eval.py`

---

## 3. Three-store reconciliation

| Store | Role | Check |
|-------|------|-------|
| DB (`documents`) | Source of truth for status/generation | `SELECT id, status, generation, chunk_count FROM documents` |
| BM25 (process memory) | Keyword recall | Restart loses index → reindex all active docs |
| Vector (memory/Chroma) | Semantic recall | Same; Chroma persists if configured |
| Object storage (`data/uploads`) | Raw bytes | `storage_key` must exist on disk/S3 |
| Revisions (`REVISION_STORE_DIR`) | Publish history | `g{N}.json` per generation |

### Consistency procedure

1. **List active docs** via Admin API; for each `storage_key`, verify object exists (`LocalObjectStorage` path `./data/uploads/...` or S3).
2. **Missing file** → mark failed or re-upload; do not reindex.
3. **DB active but retrieval empty** (after restart without reindex) → batch reindex all active.
4. **Chroma dim mismatch** after model change → recreate collection + reindex.
5. **Generation skew**: `documents.generation` should equal max revision under `revisions/{id}/`; if missing snapshot, reindex once to rewrite snapshot.
6. Health: `GET /health` — `vector` dependency reports backend; DB down → 503.

### Multi-worker notes (E12)

- Handoff claim/sweep and document index CAS are DB-safe.
- Cancel: WS `{"type":"cancel","conversation_id":"..."}` writes process registry + optional Redis key `askflow:cancel:{id}`; RAG generation honors `cancel_key=conversation_id`.
- Metrics are per-process Prometheus scrapes; aggregate in Prometheus/Grafana (see `infra/prometheus`).

---

## 4. Quick verification

```bash
cd apps/api && source .venv/bin/activate
PYTHONPATH=. pytest tests/unit/test_prd_wave_gaps.py -q
PYTHONPATH=. pytest -q
cd ../.. && PYTHONPATH=apps/api python evals/runners/run_eval.py
```
