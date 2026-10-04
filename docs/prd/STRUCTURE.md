# AskFlow 目录结构与代码导航

更新：2026-10-04，对照 `2bc7cd4`。企业产品基线见 [PRD v1.3](./PRD.md)，新增目标运行时见 [客服 Agent 方案](./customer-service-agent.md)。本页列出当前主要实现位置；目录存在不代表全部业务已启用。

## 1. 顶层

```text
AskFlow/
├── README.md                 # 项目介绍、快速开始与文档入口
├── AGENTS.md                 # 贡献者工程约定
├── CLAUDE.md                 # 助手工作指南
├── apps/
│   ├── api/                  # FastAPI 后端、迁移与测试
│   └── web/                  # React + Vite 前端
├── packages/contracts/       # Agent / API / WS 契约与 features.yaml
├── evals/                    # golden / refusals / runners / reports
├── docs/                     # 产品、架构、工程规范与可观测
├── infra/                    # Compose、反代和监控配置
├── deploy/                   # checklists 与 runbooks
├── scripts/ops/              # 代码指标检查
└── data/samples/             # 样例与查询改写词典
```

应用运行说明：[API README](../../apps/api/README.md) · [Web README](../../apps/web/README.md)。

## 2. 后端服务

以下路径相对 `apps/api/app/`。

| 路径 | 职责 / 产品范围 |
|---|---|
| `main.py` | FastAPI 装配、启动检查、后台任务生命周期 |
| `core/` | 配置、数据库、依赖注入、身份边界 |
| `plugins/` | manifest 解析、依赖闭包、装配与发现 |
| `plugins/builtin/` | 内置功能插件的路由、handler、导航注册 |
| `middleware/` | 请求日志、限流与指标 |
| `services/auth/` | JWT / RBAC / OIDC |
| `services/chat/session/` | 会话状态、消息持久化、目标受理与 Pipeline 回落 |
| `services/chat/side_effects/` | 既有消息流水线的业务副作用 |
| `services/agent/` | 目标受理、持久执行与旧消息流水线，详见下一节 |
| `services/rag/` | Honest RAG：改写、检索、证据、生成与引用 |
| `services/tools/` | 工具 Registry 与订单等工具 |
| `services/ticket/repository/` | 统一工单创建与去重入口 |
| `services/ticket/sla/` | SLA 规则与升级 |
| `services/handoff/` | 人工队列、认领、回复与超时处理 |
| `services/knowledge/` | 文件、解析、分块、索引、Gap、Draft、发布 |
| `services/prompt/` | Prompt 版本、渲染和缓存 |
| `services/llm/` | 模型客户端与 OpenAI 兼容调用 |
| `services/connectors/` | 配置化业务连接器 |
| `services/notify/` | 通知中心 |
| `services/team/` | 技能组 |
| `services/channels/` | 飞书、企微、钉钉接入 |
| `services/widget/` | 访客 Widget |
| `services/audit/`、`analytics/`、`qc/` | 审计、运营指标与质检 |

### Agent 目录

```text
services/agent/
├── identity.py               # 部署与认证客户范围
├── intake/
│   ├── chat.py               # 聊天适配、Harness 与受理回复
│   ├── judge.py              # 目标 / 直答 / 澄清 / resume 判定
│   ├── goals.py              # 目标目录、意图映射、任务/对象键
│   └── open_task.py          # 同事务创建任务与派发
├── service/
│   ├── contracts.py          # Task、Operation、Evidence、Decision 等
│   ├── registry.py           # 操作注册与前置校验
│   ├── runtime.py            # observe → verify → propose → execute
│   ├── selection.py          # 新鲜度、预算、候选去重与排序
│   ├── executor.py           # 先记录意图、调用、保存回执
│   ├── recovery.py           # 失败分类、退避、待查证与责任人检查
│   ├── store.py              # 范围隔离、版本 CAS、检查点读写
│   ├── dispatch.py           # 数据库派发租约
│   ├── delivery.py           # 下一次执行时间与按版本回写
│   ├── locks.py              # 按业务对象的范围隔离租约
│   ├── policies.py           # completion_condition → builder
│   ├── control.py            # 取消与人工接管
│   ├── lifecycle.py          # 可信事件唤醒
│   ├── driver.py             # 有界多步骤推进
│   ├── settings.py           # 总开关、目标白名单、扫描周期
│   └── order.py / chat_order.py  # 订单兼容入口
├── domains/
│   ├── order.py              # 订单契约、宿主/scoped 连接器、策略
│   ├── ticket.py             # 工单登记操作与验证
│   ├── handoff.py            # 转交入队与受理验证
│   ├── notify.py             # chat/email 候选，需宿主 sender
│   ├── refund.py             # 提交/状态操作，需宿主连接器
│   ├── support.py            # 工单/转交的认证环境与 builder
│   └── receipts.py           # 域回执辅助
├── memory/
│   ├── contracts.py / store.py  # 偏好校验与生命周期
│   ├── context.py            # 每轮偏好/事实装载，保护权威字段
│   ├── facts.py              # 已验证事实与删除传播
│   ├── events.py             # 引用型任务时间线
│   ├── experience.py         # 按目标/条件检索成功路径提示
│   └── records.py            # 统一记忆存储与 CAS
├── harness/ intent/ router/ slots/  # 共享护栏、分类与槽位
├── pipeline/                 # 直接回答与未接管业务的处理器
├── loop/                     # 原固定工具循环
├── model_router/ cost/       # 模型路由与费用
└── history_summary.py        # 作为历史数据的有界摘要
```

默认策略注册订单、工单、人工转交；默认聊天白名单仅订单。通知与退款不会因模块或目标名存在而自动执行。详细能力边界见 [Agent 差距清单](../architecture/agent-conformance.md)。

### Worker

| 路径 | 职责 |
|---|---|
| `workers/service_tasks.py` | 持久任务扫描、租约领取、对象锁、策略推进、时间线与结果回写 |
| `workers/index_worker/` | 知识索引队列消费 |
| `workers/enterprise_jobs.py` | 人工超时、SLA 等后台扫描 |

## 3. API 与模型

路由位置相对 `apps/api/app/api/v1/`，实际挂载由插件控制。

| API | 路由实现 |
|---|---|
| `/api/v1/chat/*` | `chat/` |
| `/api/v1/agent/classify` | `agent/routes.py` |
| `/api/v1/agent/tasks/*` | `agent/tasks.py`、`task_schemas.py` |
| `/api/v1/admin/service-tasks/*` | `agent/tasks.py` 的 staff_router |
| `/api/v1/agent/preferences/*` | `agent/preferences.py` |
| `/api/v1/admin/features` | `plugins_routes.py`，响应来自 `app/plugins/discovery.py` |
| `/api/v1/rag/*` | `rag/` |
| `/api/v1/tickets/*` | `tickets/` |
| `/api/v1/embedding/*` | `embedding/` |
| `/api/v1/admin/*` | `admin/` 按领域拆分 |
| `/api/v1/channels/*` | `channels/` |
| `/health`、`/metrics` | `health/routes.py`，同时挂到根路径 |

近期新增持久实体位于 `apps/api/app/models/`：

| 实体 | 文件 | 作用 |
|---|---|---|
| ServiceTask | `service_task.py` | 任务范围、版本与 JSON 检查点 |
| CustomerPreference | `customer_preference.py` | 明确确认的客户偏好 |
| ServiceDispatch | `service_dispatch.py` | 到期时间、派发租约和回写版本 |
| AgentMemory | `agent_memory.py` | fact / event / experience 统一存储 |
| ServiceObjectLock | `service_object_lock.py` | 跨任务对象租约 |

迁移目录为 `apps/api/alembic/versions/`，当前 head 是 `20261004_agent_memories_locks`。升级与已有开发数据库处理见 [API 迁移说明](../../apps/api/README.md#database-upgrades)。

## 4. 前端

当前页面与组件分层位于 `apps/web/src/`：

```text
src/
├── App.tsx                   # 路由装配与 lazy 页面
├── api/                      # HTTP 客户端、认证与类型
├── services/                 # 领域 API 与 chat-ws
├── hooks/                    # TanStack Query 与 query-keys
├── plugins/                  # features 类型、导航与路由门控
├── providers/                # QueryClient、主题与 Features
├── stores/                   # Zustand 状态
├── components/
│   ├── chat/                 # 消息、引用与转人工提示
│   ├── handoff/              # 接管工作台
│   ├── ticket/               # 工单表单、列表与详情
│   ├── admin/                # 导航、图表与管理组件
│   └── layout/               # 用户壳
└── pages/
    ├── auth/                 # 登录
    ├── user/                 # 聊天与我的工单
    ├── widget/               # 嵌入式客服
    └── admin/                # 管理页面
```

| 管理功能 | 页面文件（`pages/admin/`） |
|---|---|
| 插件与能力 | `PluginsPage.tsx`（新增，只读发现） |
| 总览 / 知识 | `DashboardPage.tsx`、`DocumentsPage.tsx`、`GapsPage.tsx`、`DraftsPage.tsx` |
| 路由 / Prompt | `IntentsPage.tsx`、`PromptsPage.tsx` |
| 工单 / 接管 / 团队 / SLA | `TicketsAdminPage.tsx`、`HandoffsPage.tsx`、`TeamsPage.tsx`、`SlaPage.tsx` |
| 治理 | `UsersPage.tsx`、`AuditPage.tsx`、`ConnectorsPage.tsx` |
| 运行与成本 | `AgentRunsPage.tsx`、`CostsPage.tsx`、`LaunchCardsPage.tsx`、`QcPage.tsx` |

当前没有服务任务、偏好、事实或经验的专门管理页。插件页调用链为 `features-service.ts → useFeaturesDiscovery → PluginsPage.tsx`。

## 5. 文档、契约与验证

| 需求 | 入口 |
|---|---|
| 企业产品基线 | [PRD.md](./PRD.md) |
| 客服 Agent 目标设计 | [customer-service-agent.md](./customer-service-agent.md) |
| 实现范围 / 待验收 | [STATUS](../STATUS.md) · [Agent 差距](../architecture/agent-conformance.md) |
| 运行、恢复与生命周期 | [运行时](../architecture/customer-service-runtime.md) · [生命周期](../architecture/customer-service-lifecycle.md) |
| 客户记忆 | [偏好、事实、事件与经验](../architecture/customer-preference-memory.md) |
| 行为 / 工程约束 | [Agent 契约](../contracts/agent-behavior.md) · [代码硬指标](../engineering/code-metrics.md) |
| 功能组合 | [features.yaml](../../packages/contracts/features.yaml) · [插件架构](../architecture/plugins.md) |
| 部署 | [deploy/checklists](../../deploy/checklists/) · [deploy/runbooks](../../deploy/runbooks/) |
| 可观测 | [observability](../observability/README.md) |

后端测试在 `apps/api/tests/unit/`、`integration/`、`e2e/`；离线语料与 runner 在 `evals/`。CI 执行 pytest、离线 eval 和 Web build；代码指标脚本为 `scripts/ops/check_code_metrics.py`。具体命令见 [README](../../README.md#开发与测试) 与 [API 专项验证](../../apps/api/README.md#verification)。
