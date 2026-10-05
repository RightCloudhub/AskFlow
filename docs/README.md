# AskFlow 文档中心

**第一次使用 AskFlow？** 请从 [用户指南 / User guide](./user-guide/README.md) 开始。指南面向没有相关经验的客户、客服与管理员，包含登录、提问、工单、人工接管、知识管理、运营配置与常见问题；正文为英文，并对照当前中文界面标签。

**需要配置安装环境或外部服务？** 阅读 [配置指南 / Configuration guide](./configuration/README.md)：从 `.env` 与首次启动讲起，涵盖功能组合、模型、存储、账号、渠道、业务连接与完整配置项参考。

| 层级 | 文档 | 说明 |
|------|------|------|
| **综合知识** | [KNOWLEDGE.md](./KNOWLEDGE.md) | **项目全貌：产品、架构、契约、配置、运维、状态与规范（单一入口）** |
| **完成状态** | [STATUS.md](./STATUS.md) | **企业基线、客服 Agent 增量、限制与复验** |
| **工程规范** | [engineering/code-metrics.md](./engineering/code-metrics.md) | **代码硬性指标（强制）** |
| 工程估算 | [engineering/pluggable-architecture-estimate.md](./engineering/pluggable-architecture-estimate.md) | 全功能可插拔工程量（L1/L2/L3） |
| 产品 | [prd/PRD.md](./prd/PRD.md) | 需求 v1.3（企业能力基线） |
| 客服 Agent | [prd/customer-service-agent.md](./prd/customer-service-agent.md) | 目标与完成条件、微步骤、独立操作与记忆 |
| 服务任务 | [architecture/customer-service-lifecycle.md](./architecture/customer-service-lifecycle.md) | 聊天受理、调度、回写、任务 API 与接管 |
| 运行时 | [architecture/customer-service-runtime.md](./architecture/customer-service-runtime.md) | 持久台账、恢复、业务域、锁与预算 |
| 客户记忆 | [architecture/customer-preference-memory.md](./architecture/customer-preference-memory.md) | 偏好管理、事实、事件与经验的接入边界 |
| Agent 验收 | [architecture/agent-conformance.md](./architecture/agent-conformance.md) | 当前能力、差距与验证证据 |
| 重构计划 | [architecture/agent-refactoring-plan.md](./architecture/agent-refactoring-plan.md) | 阶段进度与尚待完成的设计 |
| 插件 | [architecture/plugins.md](./architecture/plugins.md) | profile / features、发现接口与只读管理页 |
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

## 阅读路径（新贡献者）

1. `prd/PRD.md` §1 概览 + §10.1 MVP  
2. **`architecture/pillars.md`** → 安全 / 性能 / 记忆·可观测  
3. `architecture/agent-pipeline.md` + `rag-pipeline.md`  
4. `architecture/context-engineering.md` + `query-rewrite.md`  
5. `observability/monitoring.md`（需要完整指标表时）  
6. `contracts/agent-behavior.md`  

服务任务开发：先读 [客服 Agent 方案](./prd/customer-service-agent.md)，再读 [运行时](./architecture/customer-service-runtime.md)、[生命周期](./architecture/customer-service-lifecycle.md) 和 [记忆](./architecture/customer-preference-memory.md)；以 [差距清单](./architecture/agent-conformance.md) 区分已实现模块与已接入业务。部署配置与迁移见 [API README](../apps/api/README.md)。

## 实现时优先遵守

- **代码硬性指标**（函数 ≤50 行、文件 ≤300 行、嵌套 ≤3、位置参数 ≤3、圈复杂度 ≤10、禁魔数）：见 [engineering/code-metrics.md](./engineering/code-metrics.md)  
- Honest RAG：弱证据不调 LLM  
- Harness 安全文案不进运营模板  
- 主路径失败可降级；trace/gap best-effort  
- `/metrics` 网络隔离；日志默认脱敏  
- 会话记忆有界；默认可解释（route / refusal / sources）  
