# AskFlow 文档中心

| 层级 | 文档 | 说明 |
|------|------|------|
| 产品 | [prd/PRD.md](./prd/PRD.md) | 需求 v1.1（含 Agent 编排 / 多模型 / 成本 / Launch Card） |
| 目录 | [prd/STRUCTURE.md](./prd/STRUCTURE.md) | monorepo 文件夹映射 |
| 架构 | [architecture/](./architecture/) | 流水线 + **三大支柱** + 上下文/改写 |
| 可观测 | [observability/](./observability/) | 监控、指标目录、追踪、告警（细节） |
| 契约 | [contracts/](./contracts/) | Agent 行为硬约束 |
| 部署 | [../deploy/](../deploy/) | 检查清单与 Runbook |
| 评测 | [../evals/](../evals/) | golden / 拒答语料 |

## 三大工程支柱（实现必读）

| 支柱 | 文档 |
|------|------|
| 安全与兜底 | [architecture/security-and-fallback.md](./architecture/security-and-fallback.md) |
| 性能优化 | [architecture/performance.md](./architecture/performance.md) |
| 记忆与可观测 | [architecture/memory-and-observability.md](./architecture/memory-and-observability.md) |

索引：[architecture/pillars.md](./architecture/pillars.md)

## 阅读路径（新人）

1. `prd/PRD.md` §1 概览 + §10.1 MVP  
2. **`architecture/pillars.md`** → 安全 / 性能 / 记忆·可观测  
3. `architecture/agent-pipeline.md` + `rag-pipeline.md`  
4. `architecture/context-engineering.md` + `query-rewrite.md`  
5. `observability/monitoring.md`（需要完整指标表时）  
6. `contracts/agent-behavior.md`  

## 实现时优先遵守

- Honest RAG：弱证据不调 LLM  
- Harness 安全文案不进运营模板  
- 主路径失败可降级；trace/gap best-effort  
- `/metrics` 网络隔离；日志默认脱敏  
- 会话记忆有界；默认可解释（route / refusal / sources）  
