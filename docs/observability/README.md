# 可观测性文档索引

| 文档 | 内容 |
|------|------|
| [monitoring.md](./monitoring.md) | 总体方案：日志 / Metrics / Trace / Health / 看板 |
| [metrics-catalog.md](./metrics-catalog.md) | Prometheus 指标全表与 label 红线 |
| [tracing.md](./tracing.md) | trace_id / run_id / 逻辑 span / 多 worker |
| [alerts.md](./alerts.md) | 告警级别与建议阈值 |

## 基础设施目录

```
infra/prometheus/          # 抓取配置
infra/prometheus/rules/    # 告警规则（待落文件）
infra/grafana/dashboards/  # 看板 JSON（待落文件）
```

## MVP 最小集

1. JSON 日志 + mask + `trace_id`  
2. `/health` 依赖探活  
3. `/metrics` 核心业务指标  
4. Admin Dashboard 聚合  
5. 告警阈值文档化  

## 安全

- `/metrics` 禁止公网裸奔  
- 高基数 ID 不进 Prometheus label  
- PII 默认日志脱敏  
