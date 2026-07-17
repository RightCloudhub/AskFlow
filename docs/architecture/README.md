# 架构文档索引

AskFlow 技术架构与上下文/检索/Agent 专题。产品需求以 [PRD.md](../prd/PRD.md) 为准。

## 三大工程支柱

| 文档 | 内容 |
|------|------|
| [pillars.md](./pillars.md) | 三支柱关系与合并验收 |
| [security-and-fallback.md](./security-and-fallback.md) | 入口安全、Harness、拒答、工具降级矩阵 |
| [performance.md](./performance.md) | 延迟预算、少调模型、瘦上下文、缓存边界 |
| [memory-and-observability.md](./memory-and-observability.md) | 会话记忆分层、ContextTrace、MVP 可观测最小集 |

## RAG / Agent 专题

| 文档 | 内容 |
|------|------|
| [context-engineering.md](./context-engineering.md) | 上下文分层、历史裁剪、证据组装、Prompt 预算、ContextTrace |
| [query-rewrite.md](./query-rewrite.md) | 查询规范化 / 规则 / LLM 改写、双通道检索、与意图边界 |
| [rag-pipeline.md](./rag-pipeline.md) | Honest RAG 端到端：检索→拒答→生成→引用 |
| [agent-pipeline.md](./agent-pipeline.md) | 单次消息状态图：Harness→意图→路由→分支 |
| [plugins.md](./plugins.md) | L2 可插拔：profile、SPI、Pipeline handlers、前端装配 |

## 可观测性

见 [../observability/README.md](../observability/README.md)。

## 契约

| 文档 | 内容 |
|------|------|
| [../contracts/agent-behavior.md](../contracts/agent-behavior.md) | Agent 行为契约（实现必须遵守） |
| [../../packages/contracts/](../../packages/contracts/) | 可机器校验的契约包（骨架） |

## 设计原则（摘自 PRD）

1. 证据优先于流畅  
2. 确定性护栏优先于 Prompt 软约束  
3. 失败可降级、主流程不堵  
4. 配置热更新、契约冷更新  
5. 单租户诚实  
6. 代码即契约  
