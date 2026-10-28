# M0 阅读确认与冲突记录

日期：2026-10-29。工作分支：`feat/mall-platform`。状态：M0 设计已写入，用户 `keep going` 后采用推荐默认值继续；验证仍禁止。

本轮遵守用户的 **code only，不运行**：只阅读仓库、创建分支和编写文档。不安装依赖，不启动服务，不执行测试、eval、构建、迁移、指标脚本或压测。文档中的命令供后续授权的验证人员执行；不能据此宣称验收通过。

仓库已经存在于 `/home/arch1/AF`，直接从本地 `main` 创建分支，避免重复克隆丢失工作区上下文。已有 `apps/api/.env.example` 未提交修改，保留原状；不纳入本轮文档交付。

## 阅读材料与确认

| 已阅读材料 | 确认的约束及实现落点 |
|---|---|
| `AGENTS.md`、`CLAUDE.md` | 新增和改动文件 ≤300 行，函数 ≤50 非空行，嵌套 ≤3，位置参数 ≤3，复杂度 ≤10，业务数字使用常量；提交使用带 scope 的 conventional commits |
| `docs/engineering/code-metrics.md`、`scripts/ops/check_code_metrics.py` | Python 六项 AST 检查；TS 当前只检查文件长度；测试魔数例外不意味着函数与文件可以无限增长；脚本扫描全仓，会同时报告存量违规 |
| `README.md`、`arch.md` | 单租户、自托管、离线优先；身份等级来自可信宿主；Action Gateway 为执行关口；外部写意图必须先提交；unknown 结果不能盲重放；outbox 至少一次且消费者去重 |
| `arch.md` §4.2、§4.4、§4.11、§5、§10.6–10.7、§12–14 | 使用已有身份、台账和事件信封；模型、检索、工具结果均不授予权限；部署目标和安全清单是目标，不能当成已实现证据 |
| `docs/STATUS.md` | 原有完成声明保留；控制面配置界面、真实退款连接器/对账、生产 PG 故障切换不得未经实现及验证改成完成 |
| `docs/architecture/plugins.md` | manifest 依赖闭包、拓扑加载；关闭插件保留表，移除路由/handler/worker；原五个 profile 的清单不变 |
| `docs/architecture/action-gateway.md` | capabilities、policy、确认 nonce、幂等参数哈希、只追加台账已存在；退款要求 L2、确认、超限人工审批 |
| `customer-service-runtime.md`、`customer-service-lifecycle.md` | 默认持久目标只有订单；工单/人工可选；退款目前需宿主连接器；取消任务不等于取消业务订单；结果须独立验证 |
| `performance.md`、`security-and-fallback.md`、`memory-and-observability.md` | 安全硬停优先；依赖有限超时/重试；记忆有界；指标不得含 user_id 等高基数标签；trace 和日志遮罩复用 |
| `packages/contracts/features.yaml` | 当前 full/enterprise/mvp/faq-only/core-only；新增商城 profile，不能把商城加入旧档位 |
| `plugins/loader.py`、`context.py`、`runtime.py`、`discovery.py`、`manifest.py`、`types.py`、`builtin/*.py` | `register(ctx)` 仅装配；boot/shutdown 管生命周期；AppContext 是进程单例，测试必须重置；未启用模块不得通过顶层导入触发服务 |
| `core/config.py`、`database.py`、`main.py` | Settings 缓存；生产拒绝弱 SECRET、OIDC mock、缺 METRICS_TOKEN；本地注册服从 deny；get_db 统一提交/回滚；中间件最后添加者在最外层，当前 CORS 最外层 |
| `services/agent/gateway/` | `CapabilitySpec`、`ExecContext`、`PolicyEngine`、`LedgerStore` 可复用；当前策略金额有欧元 float，商城需独立整数分策略兼容层 |
| `domains/order.py`、`refund.py`、`ticket.py`、`handoff.py`、`notify.py` | scoped order 检查 customer/order/status；退款适配器接受 submit/status_query；工单统一仓储；人工入队不证明接单；通知需要可靠回执 |
| `services/outbox/`、`workers/` | outbox 与业务同事务；当前 relay 对未知事件直接确认，新增商城消费者必须在确认前装配；现有 worker、索引和渠道 relay 有独立开关 |
| `models/user.py`、`otp_challenge.py`、`operation_ledger.py`、`outbox.py`、`ticket.py`、`audit.py`、`mixins.py` | users 角色/邮箱/密码语义不改变；OTP 已有用途字段；财务需要额外链头/CAS而不能依赖“读最后一行”实现并发链序列化 |
| `services/auth/`、`core/security.py`、`core/deps.py` | 当前 bcrypt 与长寿命 JWT，无 refresh/session；OIDC subject 已绑定；既有认证入口与 WS 同样需要检查商城 MFA/会话吊销，防止绕过 |
| `apps/api/README.md` 的订单连接器一节 | GET 参数 `order_id,customer_id`；扁平 JSON `order_id,customer_id,status`；必须有具体状态，mock 不构成真实证据 |
| `apps/api/tests/conftest.py` | 每测试 StaticPool 内存 SQLite；替换 database.engine/SessionLocal；清 get_settings 缓存与 AppContext；旧 client fixture 固定 full，商城需独立 fixture |
| `alembic/env.py`、现有迁移链 | 当前 head 为 `20261016_document_metadata`；无初始全量企业表迁移；已有表和全新安装需要分别明确 bootstrap 流程 |
| `infra/compose/dev/docker-compose.yml`、`infra/k8s/`、Prometheus/Grafana、CI | dev 只有依赖容器；K8s 目录无可读部署清单；Grafana 只有说明；现有 CI 保持离线 API/eval/Web job，商城 full 另建 service job |
| `apps/web/src/plugins/features.tsx`、`registry.ts`、`types.ts`、`pages/` | fail-closed 默认 core；发现接口仅 agent/admin，客户无法据此发现商城；需商城公开最小发现接口，不能公开管理元数据 |
| `App.tsx`、登录/用户/后台页面、API client、theme.css | React/AntD v6；路由随 features 收敛；旧 client 401 直接退出；商城 refresh 需单飞并与认证更新事件协作；样式复用现有主题 |
| PRD、目录映射、Agent 行为契约、三大支柱 | 商城是增量域；不引入多租户计费、无限 Agent，不热改 Harness 常量、不削弱拒答与授权边界 |

## 提示词与基线的冲突处理

| 冲突/缺口 | M0 决策或待确认处理 |
|---|---|
| “只写代码不运行”与阶段要求测试全绿、构建/启动/压测达标 | 本轮仅编写实现和验证材料；阶段状态使用“已编写，未验证”，测试数量/通过率记未执行，性能数字仅为目标。完整验证见 [validation.md](./validation.md) |
| M0 要求暂停确认，而最后又要求逐步完成所有阶段 | 先写具体可评审设计；用户随后 `keep going` 授权按推荐值继续 M1–M10，保持不运行约束 |
| `mall-only` 要求无 RAG/Agent，但推荐 mall_support 强依赖 agent | ADR 003：mall_support 依赖 mall_order/ticket/handoff；Agent 为条件桥接，只有 agent 已启用才注册聊天能力；mall-only 保留人工工单，无 AI |
| mall profile = mvp 全部 + mall_notify，但 mvp 没有 notify | 保留 mvp 原清单；mall_notify 依赖闭包补 notify；mall-only 也只补 ticket/handoff/notify，无 agent/rag |
| 原身份文档把登录作为 L2，商城要求大额支付等额外验证 | 普通本地登录可满足既有客服 L2；商城资金敏感操作额外要求带短时有效、用途绑定的 step-up，不能只看 JWT 的角色 |
| 原退款策略 50 欧元、float，商城默认 CNY 整数分 | 原能力限额保持兼容；商城 mall.refund.submit 采用 currency + amount_cents，默认 5000 分，需确认币种/限额；旧 refund.submit 经商城连接器时使用商城政策 |
| 密码模块实际在 core/security.py，而非 services/auth/password | 新增共享 password 模块、保留 core/security 导出；Argon2id 默认新哈希，旧 bcrypt 登录透明迁移；MFA 防绕过覆盖所有认证入口 |
| Redis 当前在 dependencies/requirements 必装 | 移到可选 extras；同时审查既有直接导入路径，lite 安装不含客户端仍可导入旧 profile |
| 生产 lifespan 调 init_db 与提示要求生产只用迁移冲突 | ADR 004：dev/test 保留 init_db；production/staging 仅检查 schema readiness，使用一次性 migration job |
| outbox 当前无通用消费者、领取租约、退避字段 | 不改旧信封语义；新增消费回执/租约与插件消费者注册槽，商城事件在处理成功后才发布；旧推送行为兼容 |
| 财务链若沿用“读取末条后追加”会并发分叉 | ADR 005：独立财务链头行先 CAS/锁，再追加分录；账户按稳定顺序锁定；PG/SQLite 条件更新为最终一致性依据 |
| “memory 仅单实例安全”与要求 SQLite 并发防超卖 | memory 只协调本进程；资金/库存正确性始终依赖数据库条件更新/唯一约束。多实例生产拒绝 memory 协调；SQLite 使用单 API 进程 |
| full 要外部邮件/短信，但验收又要求 mock/离线 | full 预设不强制真实外发；console 默认只记录发送元数据，不能记录验证码/令牌；dev/test 验证凭据用受限测试收件箱 |
| 原用户删除能力会硬删与商城财务保留冲突 | 商城启用后删除调用先检查余额/在办订单，再脱敏停用；既有客服数据导出/删除仍通过原 service，财务保留期需运营确认 |
| 现有性能与生产故障切换只有目标无证据 | 不宣布 M9 或 PostgreSQL failover 完成；新增性能报告模板与两档部署/故障演练步骤 |

## 下一阶段入口

架构：[ADR 003](../adr/003-mall-modular-monolith.md)、[ADR 004](../adr/004-infra-ports-and-lite-mode.md)、[ADR 005](../adr/005-wallet-double-entry.md)。

评审对象：[数据设计](./data-model.md)、[API 清单](./api.md)、[状态机](./state-machines.md)、[事件](./events.md)、[能力矩阵](./infra-matrix.md)、[风险与决策](./decisions.md)。

M0 交付仅说明这些设计文档已写入分支，不说明业务代码、迁移、测试或部署已经完成。
