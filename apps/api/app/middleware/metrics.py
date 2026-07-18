"""Prometheus metrics registry (docs/observability/metrics-catalog.md)."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

HTTP_REQUESTS = Counter(
    "askflow_http_requests_total",
    "HTTP requests",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "askflow_http_request_duration_seconds",
    "HTTP latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
WS_CONNECTIONS = Gauge("askflow_ws_connections", "Active WebSocket connections")
INTENT_TOTAL = Counter(
    "askflow_intent_total",
    "Intent classifications",
    ["intent", "source"],
)
ROUTE_TOTAL = Counter(
    "askflow_route_total",
    "Routes chosen",
    ["route", "forced"],
)
HARNESS_BLOCK = Counter(
    "askflow_harness_block_total",
    "Harness blocks",
    ["stage", "reason"],
)
RAG_REFUSAL = Counter(
    "askflow_rag_refusal_total",
    "RAG refusals",
    ["reason"],
)
REWRITE_TOTAL = Counter(
    "askflow_rewrite_total",
    "Query rewrites",
    ["strategy", "status"],
)
CHAT_TURNS = Counter(
    "askflow_chat_turns_total",
    "Completed chat turns",
    ["route", "intent"],
)
PROCESS_INFO = Info("askflow_process", "Process metadata")
DEPENDENCY_UP = Gauge(
    "askflow_dependency_up",
    "Dependency health 1/0",
    ["name"],
)

# --- enterprise §9 cores ---
HANDOFF_TIMEOUT_TOTAL = Counter(
    "askflow_handoff_timeout_total",
    "Handoff sessions timed out",
)
SLA_EVENTS_TOTAL = Counter(
    "askflow_sla_events_total",
    "SLA state transitions",
    ["state", "reason"],
)
NOTIFY_TOTAL = Counter(
    "askflow_notify_total",
    "Notification delivery attempts",
    ["event", "status"],
)
LLM_ERROR_TOTAL = Counter(
    "askflow_llm_error_total",
    "LLM errors by purpose",
    ["purpose", "error_class"],
)
LLM_FALLBACK_TOTAL = Counter(
    "askflow_llm_fallback_total",
    "Model primary→fallback switches",
    ["purpose", "from_model", "to_model"],
)
CONNECTOR_TOTAL = Counter(
    "askflow_connector_total",
    "Connector invocations",
    ["name", "status"],
)
COST_USD_TOTAL = Counter(
    "askflow_cost_estimated_usd_total",
    "Estimated USD cost (scaled * 1e6 for counter integer semantics)",
    ["purpose", "model"],
)
OUT_OF_SCOPE_TOTAL = Counter(
    "askflow_out_of_scope_total",
    "Out-of-scope refusals",
)
EMBEDDING_REQUESTS = Counter(
    "askflow_embedding_requests_total",
    "Embedding batch requests",
    ["status", "backend"],
)
EMBEDDING_LATENCY = Histogram(
    "askflow_embedding_latency_seconds",
    "Embedding batch latency",
    ["backend"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
INDEX_JOBS_TOTAL = Counter(
    "askflow_index_jobs_total",
    "Knowledge index jobs",
    ["status"],
)
CANCEL_REQUESTS_TOTAL = Counter(
    "askflow_cancel_requests_total",
    "Cancel requests (conversation or run)",
    ["scope"],
)
CANCEL_HONORED_TOTAL = Counter(
    "askflow_cancel_honored_total",
    "Cancels observed mid-generation",
)
RETRIEVAL_CACHE_TOTAL = Counter(
    "askflow_retrieval_cache_total",
    "RAG retrieval cache hits/misses",
    ["result"],
)
HISTORY_SUMMARY_TOTAL = Counter(
    "askflow_history_summary_total",
    "Mid-session history compressions",
)


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
