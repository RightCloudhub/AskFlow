# 服务任务生命周期与代码导航

本阶段将 [客服 Agent 方案](../prd/customer-service-agent.md) 中的客户任务查看、取消和人工接管落到认证接口。任务仍由可信业务宿主创建；没有新增客户端任意创建目标、注入授权或指定工具的接口。

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

成功接管后，任务状态为 `handed_off`、责任人为当前人员，记录转交编号与复查时间；不标记原目标已解决。当前没有自动创建转交记录或自动领取队列的步骤，客户端必须先完成现有人工转交流程。业务宿主需在任务创建时绑定可信会话 ID；未绑定的旧任务无法直接接管。

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

尚未接入：聊天自动创建任务、自动匹配跨会话目标、后台复查调度、外部事件验签、自动创建/领取人工转交、真实退款连接器、任务费用和总时限预算。接口存在不代表这些能力已经上线。
