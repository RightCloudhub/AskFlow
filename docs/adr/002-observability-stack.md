# ADR-002：可观测性技术选型

| 项 | 内容 |
|----|------|
| 状态 | Accepted |
| 日期 | 2026-07-17 |
| 关联 | PRD §8.3；docs/observability/* |

## 背景

私有化试点需要：依赖健康、业务 SLO、运营看板、合规审计。资源有限，避免一上来重型 APM。

## 决策

1. **Prometheus** 抓取 `/metrics` + **Grafana** 看板；Alertmanager 生产再上。  
2. **JSON 结构化日志** + `trace_id` / `run_id`；默认 PII mask。  
3. **应用内 ContextTrace** 优先于强制 OTel；OTel 导出为 v1.5+ 可选。  
4. **AuditLog** 与 metrics/trace 分离（同事务、仅变更类）。  
5. Admin **Analytics** 走 PG 聚合，服务运营；不替代时序监控。  
6. `/metrics` **无鉴权但必须网络隔离**。

## 后果

- 正向：Compose 友好、单租户简单、指标口径可文档化。  
- 负向：多 worker metrics/cancel 需 Wave E 收口；分布式追踪能力弱于全量 OTel。  
- 红线：禁止 user_id 等进入 Prometheus label 基数。
