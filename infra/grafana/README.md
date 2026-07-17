# Grafana

看板规划见 [`docs/observability/monitoring.md`](../../docs/observability/monitoring.md) §7。

`dashboards/` 用于存放导出的 JSON（Overview / RAG / Agent / Handoff / Indexing / LLM）。

数据源：Prometheus。Admin Analytics 仍以应用内 PG 聚合为准，不替代本看板。
