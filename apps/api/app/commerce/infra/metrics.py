"""Low-cardinality commerce metrics in the existing Prometheus registry."""

from prometheus_client import Counter, Gauge

ORDER_TOTAL = Counter("askflow_mall_orders_total", "Committed orders", ["status"])
PAYMENT_TOTAL = Counter("askflow_mall_payments_total", "Payment outcomes", ["status"])
STOCK_SHORTAGE = Counter("askflow_mall_stock_shortage_total", "Conditional reservation failures")
OVERSOLD = Gauge("askflow_mall_oversold", "Oversold units, expected zero")
NEGATIVE_STOCK = Gauge("askflow_mall_negative_inventory", "Negative inventory rows")
CACHE_TOTAL = Counter("askflow_mall_cache_total", "Cache results", ["result"])
LIMIT_TOTAL = Counter("askflow_mall_rate_limit_total", "Rate-limit rejections", ["scope"])
BREAKER_STATE = Gauge("askflow_mall_breaker_open", "Circuit breaker state", ["adapter"])
OUTBOX_BACKLOG = Gauge("askflow_mall_outbox_backlog", "Unconsumed commerce events")
RECONCILIATION_DIFFS = Gauge("askflow_mall_reconciliation_diffs", "Open reconciliation differences")
UNBALANCED = Gauge("askflow_mall_unbalanced_journals", "Unbalanced journals, expected zero")
FLASH_QUEUE = Gauge("askflow_mall_flash_queue_length", "Unfulfilled accepted flash requests")
EVENT_RECORDS = Gauge("askflow_mall_event_records", "Persisted domain events, subject to retention", ["event"])
CALLBACK_REJECTIONS = Gauge("askflow_mall_callback_rejections_window", "Rejected signed callbacks in the last five minutes")
