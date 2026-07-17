# AskFlow 目录结构说明

> 依据 `docs/prd/PRD.md` v1.1 拆解的 monorepo 骨架。  
> 原则：**按业务域分目录**（Chat / RAG / Agent / Ticket / Handoff / Knowledge / Admin），契约与评测独立，部署与代码分离。

---

## 顶层一览

```
AF/
├── README.md                   # 项目入口
├── apps/                       # 可运行应用
│   ├── api/                    # FastAPI 后端（§3.3）
│   └── web/                    # React + Vite 前端（§3.3）
├── packages/                   # 跨端共享：类型、契约、语料
├── evals/                      # 离线评估（§4.2.3 / §9）
├── docs/                       # 文档中心
│   ├── prd/                    # 产品需求与目录映射（本文件所在）
│   │   ├── PRD.md              # 产品需求（源文档）
│   │   ├── STRUCTURE.md        # 本文件：目录 ↔ PRD 映射
│   │   └── README.md           # 产品文档索引
│   ├── architecture/           # 上下文工程 · 改写 · RAG · Agent
│   ├── observability/          # 监控 · 指标 · 追踪 · 告警
│   ├── contracts/              # 行为契约（人类可读）
│   ├── adr/                    # 架构决策记录
│   └── runbooks/               # 运维手册索引
├── infra/                      # Compose / 反代 / 可观测 / K8s
│   ├── prometheus/             # 抓取与 rules/
│   └── grafana/dashboards/     # 看板 JSON
├── deploy/                     # 生产检查清单与 Runbook（§S-04）
├── scripts/                    # 开发 / 部署 / 运维脚本
├── data/                       # 样例与测试夹具（含 query_synonyms）
└── .github/workflows/          # CI（eval 门禁 v1.5+）
```

---

## 1. `apps/api` — 后端（FastAPI）

对应 PRD §3 架构、§4 功能、§7 接口。

```
apps/api/
├── alembic/                    # SQLAlchemy 迁移
│   └── versions/
├── app/
│   ├── main.py                 # 应用入口；生产密钥 fail-safe（§4.1 / S-01）
│   ├── api/v1/                 # REST 分组（§7.1）
│   │   ├── admin/
│   │   │   ├── auth/           # register / login / me
│   │   │   ├── documents/      # 文档列表 / 删除
│   │   │   ├── intents/        # 意图 CRUD（§4.10.1）
│   │   │   ├── prompts/        # 模板与版本（§4.10.2）
│   │   │   ├── analytics/      # 运营分析（§4.12.1）
│   │   │   ├── tickets/        # 管理工单与看板
│   │   │   ├── system/         # /admin/system/health
│   │   │   ├── handoffs/       # 接管收件箱（§4.7）
│   │   │   ├── audit_logs/     # 审计查询（§4.11）
│   │   │   ├── gaps/           # 知识缺口（§4.9）
│   │   │   └── drafts/         # 草稿审核
│   │   ├── chat/               # 会话 / 消息 / WS / 反馈（§4.5）
│   │   │   ├── conversations/
│   │   │   ├── messages/
│   │   │   ├── ws/
│   │   │   └── feedback/
│   │   ├── rag/                # /rag/query 同步查询
│   │   ├── agent/              # /agent/classify 调试
│   │   ├── tickets/            # 用户侧工单 CRUD（§4.6）
│   │   ├── embedding/          # 上传 / reindex（§4.8）
│   │   └── health/             # /health · /metrics
│   ├── core/                   # 配置、DB、Redis、依赖注入
│   ├── plugins/                # L2 可插拔：manifest 装配 · builtin 包 · SPI
│   ├── middleware/             # CORS · 限流 · 日志 · 异常 · metrics
│   ├── models/                 # ORM 实体（§6）
│   ├── schemas/                # Pydantic DTO
│   ├── services/               # 领域服务（业务核心）
│   │   ├── auth/               # JWT · 密码哈希 · RBAC
│   │   ├── chat/               # 会话状态 · WS 协议 · 反馈
│   │   ├── rag/                # Honest RAG 流水线（§4.2）
│   │   │   ├── query_rewrite/  # 查询规范化 / 规则 / 可选 LLM 改写
│   │   │   ├── context/        # 历史裁剪 · 证据块 · 预算组装
│   │   │   ├── bm25/           # 关键词召回
│   │   │   ├── vector/         # 向量召回（Chroma）
│   │   │   ├── fusion/         # 融合 / rerank hook
│   │   │   ├── grounding/      # 证据评估与拒答
│   │   │   ├── generator/      # 流式生成 + Prompt 组装
│   │   │   └── citations/      # 行内引用自检
│   │   ├── agent/              # 意图 · 路由 · Harness · Loop（§4.3 / §4.13）
│   │   │   ├── harness/        # prepare / choose_route / finalize
│   │   │   ├── intent/         # 规则 + LLM 分类
│   │   │   ├── router/         # 运营配置 + 内置兜底
│   │   │   ├── slots/          # 槽位状态机（§4.4.2）
│   │   │   ├── loop/           # plan→act→observe→recover（§4.13）
│   │   │   ├── model_router/   # purpose → 模型链 / fallback（§4.14）
│   │   │   ├── cost/           # Cost Ledger 记账（§4.17）
│   │   │   └── pipeline/       # 流水线 + handlers/* 表驱动（§3.2 / 可插拔）
│   │   ├── tools/              # 工具注册（§4.4）
│   │   │   ├── search_order/
│   │   │   └── search_knowledge/
│   │   ├── ticket/             # 工单仓储 · 去重 · 看板
│   │   │   ├── repository/     # 统一创建入口（红线）
│   │   │   ├── board/
│   │   │   └── sla/            # MVP 统计；v2 分级引擎
│   │   ├── handoff/            # 暖转人工（§4.7）
│   │   │   ├── queue/
│   │   │   ├── summary/
│   │   │   ├── claim/          # 认领 409
│   │   │   └── timeout/        # 清扫逻辑
│   │   ├── knowledge/          # 知识库 + 自进化（§4.8–4.9）
│   │   │   ├── storage/        # 对象存储原文件
│   │   │   ├── parser/         # PDF / MD / TXT
│   │   │   ├── chunker/        # size=500, overlap=50
│   │   │   ├── indexer/        # write-new-then-delete
│   │   │   ├── gap/            # 缺口雷达
│   │   │   └── draft/          # Draft 审核发布
│   │   ├── prompt/             # 模板版本 · 缓存 · 渲染
│   │   ├── audit/              # 审计 + 脱敏（§4.11）
│   │   └── analytics/          # Dashboard 指标聚合
│   ├── workers/                # 异步 worker（§4.8 / §4.7.5）
│   │   ├── index_worker/       # 文档索引消费
│   │   └── handoff_sweeper/    # 超时清扫（SKIP LOCKED）
│   └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/                    # 主路径 E2E（v1.5+）
└── scripts/
```

### 服务 ↔ PRD 能力映射

| 目录 | PRD 章节 | MVP 关键能力 |
|------|----------|--------------|
| `services/rag/query_rewrite` | §4.2 / P3 | 规范化 + 同义规则改写 |
| `services/rag/context` | §4.2.1 | 历史预算、证据组装、ContextTrace |
| `services/rag/*` | §4.2 | 混合检索、拒答、引用、置信度 |
| `services/agent/*` | §4.3 | 6 意图、Harness、5 类路由 |
| `services/tools/*` | §4.4 | search_order + 槽位 |
| `services/chat/*` | §4.5 | REST + WS 协议 |
| `services/ticket/*` | §4.6 | 去重、看板 |
| `services/handoff/*` | §4.7 | 入队、认领、超时 |
| `services/knowledge/*` | §4.8–4.9 | 异步索引、Gap→Draft |
| `services/prompt/*` | §4.10 | 热更新 + 回滚 |
| `services/audit/*` | §4.11 | 同事务审计 + 脱敏 |
| `services/analytics/*` | §4.12 | 运营看板数据 |

---

## 2. `apps/web` — 前端（React + Vite）

对应 PRD §4.5.3 用户页、§4.12.3 Admin 页面地图。

```
apps/web/src/
├── api/                        # HTTP / WS 客户端
├── components/
│   ├── chat/                   # 消息流、输入、来源、置信度 badge、转人工横幅
│   ├── ticket/                 # 工单列表 / 详情 / 表单 / 看板
│   ├── handoff/                # 收件箱、认领
│   ├── layout/
│   └── common/
├── features/
│   ├── auth/                   # 登录注册（U-01）
│   ├── chat/                   # 用户工作台（§4.5.3）
│   ├── tickets/                # 我的工单（U-09）
│   ├── settings/
│   └── admin/                  # 运营后台（§4.12.3）
│       ├── dashboard/          # 总览 + 系统健康
│       ├── tickets/            # 工单与 SLA 统计
│       ├── documents/          # 文档与索引
│       ├── intents/            # 意图路由
│       ├── prompts/            # 提示词版本
│       ├── gaps/               # 知识缺口
│       ├── drafts/             # 草稿审核（Knowledge）
│       ├── handoffs/           # 接管收件箱
│       ├── audit/              # 审计日志
│       └── users/              # 用户管理（v1.5+）
├── pages/
│   ├── auth/
│   ├── user/                   # 用户侧页面路由壳
│   └── admin/                  # Admin 路由壳
├── routes/                     # 角色门控（user / agent / admin）
├── hooks/
├── stores/
├── types/
├── utils/
└── styles/
```

### Admin 页面 ↔ 目录

| Admin 页面（§4.12.3） | 目录 |
|----------------------|------|
| Dashboard | `features/admin/dashboard` |
| Tickets / Ticket Dashboard | `features/admin/tickets` |
| Documents | `features/admin/documents` |
| Intents | `features/admin/intents` |
| Prompts | `features/admin/prompts` |
| Gaps | `features/admin/gaps` |
| Knowledge（草稿） | `features/admin/drafts` |
| Handoffs | `features/admin/handoffs` |

---

## 3. `packages/` — 共享包

```
packages/
├── shared-types/               # 前后端共用枚举与 DTO（§6.2）
│   ├── enums/                  # UserRole, ConversationStatus, …
│   └── dto/
├── contracts/                  # 代码即契约（§1.5 原则 6）
│   ├── agent/                  # 意图 / 路由 / 工具 / Harness / Handoff 行为契约
│   ├── api/                    # REST envelope / 错误码
│   └── ws/                     # WebSocket 帧类型（§4.5.2）
└── eval-corpus/                # 可复用评测样本包
```

对应附录 C：`AGENTS.md` 级行为契约放 `packages/contracts/agent/`。

---

## 4. `evals/` — 离线评估

对应 §4.2.3、§9、验收标准 §12.1 #3。

```
evals/
├── golden/                     # FAQ 命中 / 引用有效性
│   ├── faq/
│   ├── product/
│   └── order/
├── refusals/                   # 拒答用例
│   ├── weak_evidence/
│   ├── injection/
│   └── out_of_scope/           # Wave A E4
├── runners/                    # 跑评测脚本
└── reports/                    # 输出报告（CI 产物）
```

---

## 5. `docs/` — 文档

对应附录 C 文档分工。入口：[docs/README.md](../README.md)。

```
docs/
├── README.md                   # 文档中心与新人阅读路径
├── prd/
│   ├── README.md               # 产品文档索引
│   ├── PRD.md                  # 产品需求（源文档）
│   └── STRUCTURE.md            # 本文件：目录 ↔ PRD 映射
├── architecture/
│   ├── context-engineering.md  # 上下文分层 / 预算 / Trace
│   ├── query-rewrite.md        # 查询改写策略
│   ├── rag-pipeline.md         # Honest RAG 全链路
│   └── agent-pipeline.md       # 单次消息 Agent 流水线
├── observability/
│   ├── monitoring.md           # 监控总方案
│   ├── metrics-catalog.md      # Prometheus 指标全表
│   ├── tracing.md              # run_id / span
│   └── alerts.md               # 告警阈值
├── contracts/
│   └── agent-behavior.md       # 实现必守契约
├── adr/
│   ├── 001-context-and-rewrite.md
│   └── 002-observability-stack.md
└── runbooks/                   # 运维手册索引（正文也可在 deploy/）
```

| 问题 | 落点 |
|------|------|
| 产品边界 / 分期 / 验收 | `docs/prd/PRD.md` |
| 目录结构与 PRD 映射 | `docs/prd/STRUCTURE.md` |
| 上下文怎么裁、证据怎么装 | `docs/architecture/context-engineering.md` |
| 口语/指代如何检索 | `docs/architecture/query-rewrite.md` |
| 监控什么、告警什么 | `docs/observability/*` |
| Agent 行为契约 | `docs/contracts` + `packages/contracts/agent` |
| 怎么部署 | `deploy/checklists` + `deploy/runbooks` |
| 为什么这样设计 | `docs/adr` |

---

## 6. `infra/` — 基础设施

对应 §3.4 部署拓扑、§8.3 可观测性、附录 A 配置。

```
infra/
├── docker/                     # API / Web / Worker 镜像
├── compose/
│   ├── dev/                    # PG · Redis · Chroma · MinIO
│   └── prod/                   # 试点生产参考
├── nginx/                      # TLS 终结反代
├── prometheus/                 # 抓取配置
├── grafana/                    # 看板（试点后按环境）
└── k8s/                        # 企业目标（可选）
    ├── base/
    └── overlays/
```

---

## 7. `deploy/` — 上线与运维

对应 S-04、§10.1 部署交付、Wave E Runbook。

```
deploy/
├── checklists/                 # 生产启动检查（默认 SECRET 拒启等）
└── runbooks/                   # reindex / 模型轮换 / 三存储对账
```

---

## 8. 数据模型实体 ↔ ORM 建议文件

落地时放 `apps/api/app/models/`（§6.1）：

| 实体 | 建议文件 |
|------|----------|
| User | `user.py` |
| Conversation / Message | `conversation.py`, `message.py` |
| Feedback | `feedback.py` |
| Ticket | `ticket.py` |
| HandoffSession | `handoff.py` |
| Document | `document.py` |
| KnowledgeGap / KnowledgeDraft | `gap.py`, `draft.py` |
| PromptTemplate / PromptVersion | `prompt.py` |
| IntentConfig | `intent.py` |
| AuditLog | `audit.py` |

---

## 9. REST 前缀 ↔ 路由目录

| API 前缀（§7.1） | 代码位置 |
|------------------|----------|
| `/api/v1/admin/auth/*` | `api/v1/admin/auth` |
| `/api/v1/chat/*` | `api/v1/chat` |
| `/api/v1/rag/query` | `api/v1/rag` |
| `/api/v1/agent/classify` | `api/v1/agent` |
| `/api/v1/tickets/*` | `api/v1/tickets` |
| `/api/v1/embedding/*` | `api/v1/embedding` |
| `/api/v1/admin/documents` | `api/v1/admin/documents` |
| `/api/v1/admin/intents` | `api/v1/admin/intents` |
| `/api/v1/admin/analytics` | `api/v1/admin/analytics` |
| `/api/v1/admin/tickets*` | `api/v1/admin/tickets` |
| `/api/v1/admin/system/health` | `api/v1/admin/system` |
| `/api/v1/admin/handoffs/*` | `api/v1/admin/handoffs` |
| `/api/v1/admin/prompts/*` | `api/v1/admin/prompts` |
| `/api/v1/admin/audit-logs` | `api/v1/admin/audit_logs` |
| `/api/v1/admin/gaps/*` | `api/v1/admin/gaps` |
| `/api/v1/admin/drafts/*` | `api/v1/admin/drafts` |
| `/health` · `/metrics` | `api/v1/health` |

---

## 10. 分期目录预留（暂不实现，仅占位语义）

| Wave | PRD | 建议扩展点 |
|------|-----|------------|
| A E1 SLA 引擎 | §10.2 | `services/ticket/sla/` 升级为主动扫描 |
| A E2 通知中心 | §10.2 | 新增 `services/notify/` |
| A E4 out_of_scope | §10.2 | `services/agent/intent/` + `evals/refusals/out_of_scope/` |
| B 技能组 | §10.3 | 新增 `services/team/` + `features/admin/teams/` |
| C SSO | §10.4 | `services/auth/` 扩展 OIDC |
| C 连接器 | §10.4 | 新增 `services/connectors/` |
| C Widget | §10.4 | 新增 `apps/widget/` |
| E IM 渠道 | §10.6 | 新增 `apps/channels/feishu|wecom|dingtalk/` |

---

## 11. MVP 优先实现顺序（与目录对应）

按 PRD §10.1 建议任务板：

1. **infra/compose/dev** + **apps/api/core** — 依赖可起
2. **auth** — 登录门控
3. **chat/ws + agent/pipeline + harness** — 实时对话主链
4. **rag/*** — Honest RAG
5. **tools/search_order + slots** — 订单槽位
6. **ticket + handoff** — 工单与暖转
7. **knowledge/indexer + gap + draft** — 知识闭环
8. **prompt + audit + analytics** — 运营平台
9. **web features** — 用户台 + Admin 页
10. **evals + deploy/checklists** — 试点门槛

---

## 12. 目录统计

- 业务骨架目录约 **180+**（含占位）
- 空目录已放 `.gitkeep`，可直接 `git add`

下一步：在 `apps/api` / `apps/web` 初始化工程脚手架，或按 §10.1 拆任务板到 issue。
