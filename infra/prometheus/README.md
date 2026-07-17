# Prometheus

- 指标语义与命名：[`docs/observability/metrics-catalog.md`](../../docs/observability/metrics-catalog.md)
- 告警建议：[`docs/observability/alerts.md`](../../docs/observability/alerts.md)
- 规则文件：`rules/`（实现阶段写入 `askflow.yml`）
- 抓取目标：API `/metrics`（**仅内网**）

试点 Compose 可增加 `prometheus` + `grafana` 服务，挂载本目录与 `../grafana/dashboards/`。
