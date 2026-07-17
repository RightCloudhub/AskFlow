# AskFlow

企业智能客服系统（RAG + Agent）— 单租户、可私有化部署。

## 文档

| 文档 | 说明 |
|------|------|
| [docs/prd/PRD.md](./docs/prd/PRD.md) | 产品需求（**v1.1** · Agent 编排 / 多模型 / 成本 / Launch Card） |
| [docs/prd/STRUCTURE.md](./docs/prd/STRUCTURE.md) | 目录结构与 PRD 映射 |
| [docs/README.md](./docs/README.md) | **文档中心**（推荐入口） |
| [docs/architecture/](./docs/architecture/) | 上下文工程 · 查询改写 · RAG · Agent |
| [docs/observability/](./docs/observability/) | 监控 · 指标 · 追踪 · 告警 |
| [docs/contracts/agent-behavior.md](./docs/contracts/agent-behavior.md) | Agent 行为契约 |

### 三大工程支柱

| 支柱 | 文档 | 一句话 |
|------|------|--------|
| 安全与兜底 | [security-and-fallback](./docs/architecture/security-and-fallback.md) | Harness + 拒答 + 工具/依赖降级矩阵 |
| 性能优化 | [performance](./docs/architecture/performance.md) | 少调贵模型、瘦上下文、异步索引 |
| 记忆与可观测 | [memory-and-observability](./docs/architecture/memory-and-observability.md) | 有界会话记忆 + logs/metrics/trace |

总索引：[pillars.md](./docs/architecture/pillars.md)

### 架构专题速览

| 专题 | 一句话 |
|------|--------|
| [上下文工程](./docs/architecture/context-engineering.md) | L0–L4 分层；历史预算；证据组装；ContextTrace |
| [查询改写](./docs/architecture/query-rewrite.md) | 默认规则同义；LLM 改写可选且可回落 |
| [Honest RAG](./docs/architecture/rag-pipeline.md) | 混合检索 → Grounding 拒答 → 流式引用 |
| [Agent 流水线](./docs/architecture/agent-pipeline.md) | Harness → 意图 → 路由 → 五类节点 |
| [监控细节](./docs/observability/monitoring.md) | 完整看板与指标扩展 |

## 仓库结构（摘要）

```
apps/api          # FastAPI 后端
apps/web          # React + Vite 前端
packages/         # 共享类型与行为契约
evals/            # 离线 golden / 拒答评测
docs/             # 架构 · 可观测 · 契约 · ADR
infra/            # Compose / 反代 / Prometheus / Grafana
deploy/           # 生产检查清单与 Runbook
data/samples/     # 含 query_synonyms.yaml 等样例
```

详见 [docs/prd/STRUCTURE.md](./docs/prd/STRUCTURE.md)。

## 技术选型（PRD §3.3）

| 层 | 技术 |
|----|------|
| API | FastAPI |
| ORM | SQLAlchemy 2 async + Alembic |
| 向量 | ChromaDB（MVP） |
| 队列 | Redis |
| 对象存储 | MinIO / S3 |
| 前端 | React + Vite |
| LLM | OpenAI 兼容 API |
| 监控 | Prometheus + Grafana（JSON 日志 + trace_id） |

## 代码落点（核心能力）

| 能力 | 代码位置 |
|------|----------|
| 查询改写 | `apps/api/app/services/rag/query_rewrite/` |
| 上下文组装 | `apps/api/app/services/rag/context/` |
| Honest RAG | `apps/api/app/services/rag/` |
| 意图 / Harness | `apps/api/app/services/agent/` |
| 工单 / 暖转 | `services/ticket/` · `services/handoff/` |
| 知识 / Gap | `services/knowledge/` |
| 指标埋点 | `middleware/` · `api/v1/health` |
| 用户台 / Admin | `apps/web/src/features/` |

## 状态

- 目录骨架与**工程文档**（上下文 / 改写 / 监控）已就绪  
- 应用运行时代码尚未初始化  

## 建议下一步

1. 初始化 `apps/api` + `apps/web` 脚手架  
2. 按 MVP：auth → pipeline → rag(含 rewrite/context) → metrics  
3. 将 `docs/observability/metrics-catalog.md` 落成 Prometheus 客户端注册表  
