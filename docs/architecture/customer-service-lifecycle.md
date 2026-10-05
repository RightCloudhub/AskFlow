# 服务任务生命周期与代码导航

更新：2026-10-04，对照 `2bc7cd4`。[客服 Agent 方案](../prd/customer-service-agent.md) 已接入聊天受理、持久派发、客户任务查看、取消与验证接管。任务由认证聊天入口或可信宿主创建，没有客户端任意指定目标和工具的创建接口。

## 聊天受理与后台派发

`chat/session/turn.py` 在会话为 active 时先调用 `agent/intake/chat.py`。受理前运行 Harness，分类后由 `judge.py` 判定目标、直答或澄清；订单缺号继续使用原槽位流程。默认只接管 `order_status`，`ticket_resolution` 与 `human_handoff` 需加入 `SERVICE_TASKS_GOALS`。未接管消息回到原流水线，已建任务不再重复执行原工单/转交副作用。

任务 ID 由会话、目标和可选业务对象推导，同一会话重复请求复用同一任务。订单以订单号区分，工单/转交当前以会话和目标去重，不能据此宣称同会话多项工单目标或跨会话自动续办。`judge(open_task=...)` 虽支持 resume 判定，聊天入口尚未查询在办任务或执行该分支。

用户消息、受理回复、`service_tasks` 检查点与 `service_dispatches` 记录在同一事务提交；任何一步失败整体回滚。客户先收到受理确认，worker 随后通过目标策略推进任务。

| 派发机制 | 当前行为 |
|---|---|
| 启动条件 | Agent 插件启用且 `SERVICE_TASKS_ENABLED=true`；test 环境不启动后台循环 |
| 扫描 | 默认每 5 秒；每批最多 20 项，数据库条件更新领取 300 秒租约 |
| 执行 | 按 `completion_condition` 查 builder；单次派发最长 240 秒 |
| 自动续跑 | active 任务重新排队；`waiting_external` 且 `wake_condition=retry:*` 按 `review_at` 唤醒 |
| 对象冲突 | 订单对象租约竞争失败则重新排队，不执行该对象的操作 |
| 派发故障 | 有界重试；失败耗尽进入责任人检查，存储仍失败时需运维修复 |
| 其他等待 | `owner_review:*`、客户补充、人工接单和外部事件不自动订阅或扫描唤醒 |

关闭总开关并重启 API 会同时停用受理与 worker；从目标白名单移除某项只影响新受理，已有任务仍按注册策略推进。配置与回滚行为见 [API README](../../apps/api/README.md#service-tasks-and-order-connector)。

## 结果回写

`finish_dispatch` 同事务释放租约、安排下一次执行并按任务版本去重写入助手消息。只向当前客户的 active 会话写入；取消或接管后的任务不再追加自动回复。回写前再检查任务版本，避免把旧结果写入已变化的任务。

验证通过的订单状态或工单登记结果可回写；未解决任务只显示需支持人员检查，不暴露未验证回执。当前没有后台结果 WebSocket 广播，重新读取会话消息即可取得更新。工单任务的 `resolved` 当前表示登记成功，不能解释为原故障已修复。

## 接口与使用场景

| 请求 | 使用场景与约束 |
|---|---|
| `GET /api/v1/agent/tasks?limit=20&after=UUID` | 查看本人跨会话任务，按 task_id 升序游标分页；最多 100 条 |
| `GET /api/v1/agent/tasks/{task_id}` | 查看本人任务状态；他人任务与不存在任务均返回 404 |
| `POST /api/v1/agent/tasks/{task_id}/cancel` | 客户取消尚未结束的目标，要求当前版本 |
| `POST /api/v1/admin/service-tasks/{task_id}/accept-handoff` | 当前接待人员绑定自己已领取的转交记录并接管任务 |

返回的任务摘要仅包含 `task_id`、`goal`、`status`、`version`、`review_at`、`has_unsettled_operations`。不返回内部操作参数、业务回执、授权信息和诊断台账。分页不是跨请求一致性快照，并发插入的新任务可能需要从首页重新查看。

取消请求：

```json
{"expected_version": 0, "reason": "客户不再需要办理"}
```

人工接管请求：

```json
{"expected_version": 0, "handoff_id": "已领取的转交记录 UUID"}
```

参数不合法返回 422，版本过期或状态不允许返回 409。取消接口仅允许 `active`、`waiting_customer`、`waiting_external` 转为 `closed_unresolved`；不能将已解决或已接管的任务重新分类。调用者必须登录，不能从请求设置组织或客户范围。

## 人工接管的事务边界

调用者必须具有 agent/admin 角色，且对应 `HandoffSession` 必须为 `claimed`、`claimed_by` 等于当前人员。服务从转交记录派生客户范围，再核对任务的 `conversation_id`，避免把另一客户或另一会话的任务接到当前队列。

领取记录通过条件更新锁定，任务读取与版本更新在同一数据库事务中执行。此方式兼容 SQLite 的写锁和 PostgreSQL 的行锁。条件失效、会话不匹配、任务版本冲突时整体回滚。

成功接管后，任务状态为 `handed_off`、责任人为当前人员，记录转交编号与复查时间；不标记原目标已解决。启用 `human_handoff` 可由任务操作自动入队，但当前仍无自动领取和接单事件唤醒；人员须先完成现有队列领取，再调用本接口。宿主创建的任务也需绑定可信会话 ID；未绑定的旧任务无法直接接管。

## 已发出操作的处理

取消和接管增加任务版本，阻止旧快照提交新的执行意图。已经提交意图并发出的请求可能继续完成，不能将控制状态变化解释为业务撤销。

原操作的 `running` / `unknown` 台账不会清空，累计预算不重置；取消后仍有未确定操作时保留责任人、复查时间与检查条件。接管者需按原业务请求键对账。旧执行器若无法提交回执，将得到版本冲突；不要通过重放写请求恢复。

生命周期变化保存在任务检查点中的 `transitions`，包含前后状态、操作者、原因与时间，作为业务追踪数据使用。原因文本不会获得指令权限。新字段有默认值，现有检查点无需表结构迁移即可读取。

## 代码组织

| 层次 | 位置 | 职责 |
|---|---|---|
| HTTP 边界 | `apps/api/app/api/v1/agent/tasks.py`、`preferences.py` | 认证、请求校验、状态码映射 |
| 对外任务结构 | `apps/api/app/api/v1/agent/task_schemas.py` | 客户可见摘要，屏蔽内部台账 |
| 身份映射 | `apps/api/app/services/agent/identity.py` | 任务与偏好接口共享部署和客户范围 |
| 目标受理 | `apps/api/app/services/agent/intake/` | 判定、目标目录、去重和同事务建任务 |
| 域与策略装配 | `apps/api/app/services/agent/domains/`、`service/policies.py` | 独立操作与目标 builder |
| 后台派发 / 回写 | `apps/api/app/workers/service_tasks.py`、`services/agent/service/dispatch.py`、`delivery.py` | 租约、到期重试与按版本回写 |
| 业务状态转换 | `apps/api/app/services/agent/service/control.py` | 取消、人工接管、版本与归属校验 |
| 事件唤醒 | `apps/api/app/services/agent/service/lifecycle.py` | 可信事件唤醒，重试退避校验 |
| 决策与操作 | `apps/api/app/services/agent/service/runtime.py`、`executor.py`、`recovery.py` | 观察、选择、执行、恢复 |
| 任务存储 | `apps/api/app/services/agent/service/store.py` | 范围过滤、分页、独立事务与宿主事务内的版本更新 |
| 可选客户记忆 | `apps/api/app/services/agent/memory/` | 客户确认、纠正、删除和每轮读取 |
| 持久模型与迁移 | `apps/api/app/models/`、`apps/api/alembic/versions/` | 检查点、偏好与版本化数据库迁移 |

`TaskStore.save` 独立提交；`load_in_transaction` 与 `write_checkpoint` 供宿主组合原子事务使用。后者不自动提交，也不修改内存版本，调用者必须在事务成功后递增版本。

## 验证与剩余边界

相关测试：`tests/unit/test_service_control.py`、`tests/integration/test_service_tasks_api.py`，覆盖客户隔离、摘要过滤、分页、版本冲突、取消后旧执行器、未知副作用保留、未领取/非本人/不同会话的接管拒绝，以及取消和接管并发竞争。

同时回归运行基础、偏好 API 与迁移测试。实际生产 PostgreSQL 并发与故障切换仍需独立环境验证。

新增验证入口：`tests/integration/test_chat_service_tasks.py`、`test_agent_conformance.py` 与 `tests/unit/test_service_dispatch.py`、`test_service_locks.py`，覆盖消息/任务事务回滚、重发去重、租约到期恢复、到期重试、工单接管和结果回写。

尚未接入：自动匹配跨会话目标、聊天 waiting_customer 续办、多目标依赖图、外部事件验签、自动领取人工转交及真实退款连接器。任务费用/截止时间已有运行时校验，但默认聊天任务未设置这两项；费用还依赖宿主提供估计。完整边界见 [差距清单](./agent-conformance.md)。
