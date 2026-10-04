# 客户记忆：偏好接口、事实、事件与经验

更新：2026-10-04，对照 `2bc7cd4`。对应 [客服 Agent 方案](../prd/customer-service-agent.md) 的记忆生命周期。偏好已有客户 API；事实、事件和经验已有内部存储接口，其自动化接入范围各不相同。

## 已支持的偏好

| key | value | 用途 |
|---|---|---|
| `language` | `zh-CN`、`en` | 候选方案和回复的语言偏好 |
| `response_detail` | `brief`、`detailed` | 回复详细程度 |
| `contact_channel` | `chat`、`email` | 方案比较时的联系渠道偏好 |

联系偏好不构成发送邮件或外部通知的授权。所有偏好都不改变身份、业务权限、订单归属或可用工具。拒绝未知字段、自由文本、凭据及未明确确认的写入。

## 认证接口

接口由 Agent 插件注册，均要求已有登录 Bearer token；访客 token 不可使用。当前账号模型没有组织成员关系，HTTP 入口使用固定 `deployment` 范围及认证用户 ID，不从请求接受客户或组织标识。多租户产品接入前需要从可信成员关系派生组织范围；底层存储及 Agent 读取已同时按组织和客户过滤。

| 请求 | 行为 |
|---|---|
| `GET /api/v1/agent/preferences` | 查看本人偏好、版本、来源、有效期及状态 |
| `PUT /api/v1/agent/preferences` | 明确确认后创建或按版本纠正偏好 |
| `DELETE /api/v1/agent/preferences/{key}?expected_version=N` | 按版本删除本人偏好值 |

创建请求：

```json
{
  "key": "language",
  "value": "zh-CN",
  "consent": true,
  "expected_version": 0,
  "retention_days": 30
}
```

默认保留 30 天，允许 1–90 天。修改时再次明确提供 `consent: true`，并使用 GET 返回的最新版本。每次成功修改或删除递增版本；冲突返回 `409 preference_version_conflict`，客户端应重新读取后让客户决定，不自动覆盖较新的修改。无效值或缺少确认返回 422。

响应包含 `memory_id`、`key`、`value`、`version`、`status`、`source`、`retention_basis`、`verified_at`、`expires_at`。`source` 固定为 `customer_confirmed`，保留依据固定为 `explicit_consent`。删除或到期的记录返回 `value: null`，便于客户使用当前版本重新确认。

## Agent 使用与故障行为

`ServiceAgent` 每轮在环境观察后，从 `PreferenceStore` 重新读取当前任务范围内未到期的偏好，供业务策略通过 `Environment.preferences` 使用。本轮由宿主明确设置的选择优先于历史偏好，不会自动写回长期记忆。

新运行时通过 `with_memory` 每轮读取偏好和事实；原聊天流水线尚未使用这些偏好。通知适配器会使用 `contact_channel` 比较候选，但尚未接入默认 worker；当前聊天订单回写仍为固定文案。保存语言或详细程度偏好不代表回复已经自动改变。

偏好没有缓存，也不由运行时复制到任务检查点。删除清空主表的值，保留不含偏好内容的版本标记，防止持有旧版本的请求重新创建内容。业务策略不得将偏好原值重新缓存为事实或写进持久化决策摘要；若扩展其他副本，必须接入统一删除机制。

到期记录立即停止影响决策；当前没有定时物理清理任务。备份恢复流程仍需独立处理删除记录与恢复后的保留规则，本阶段不保证任意旧备份恢复后的删除一致性。

偏好是可选上下文。读取超时、数据库不可用或存储内容校验失败时，运行时保留本轮明确选择并将 `preference_status` 设为 `unavailable`，继续正常任务；`memory_status` 汇总记忆读取状态。诊断日志只记录错误类型。偏好 API 的写入失败不会被伪装成保存成功。订单等实时事实仍需查询业务系统。

## 事实、事件与经验的当前接入

| 类型 | 实现 | 接入边界 |
|---|---|---|
| 客户事实 | `FactStore`：明确确认/回执引用验证、范围过滤、版本纠正、有效期和墓碑删除 | 每轮由 `with_memory` 读取；无客户事实 API、管理页或聊天自动提取 |
| 事件时间线 | `TimelineStore`：从状态转换与非 running 操作生成稳定事件 ID | worker 推进任务后追加；无公共时间线 API，非全部状态变化的统一审计流 |
| 经验提示 | `ExperienceStore`：保存路径，按目标及全部条件匹配成功经验 | 仅内部 record/suggest；未自动从任务写入，也未接入默认策略消费 |

三个存储均位于 `apps/api/app/services/agent/memory/`，使用 `agent_memories` 表并按组织/客户隔离，默认有效期 30 天。

事实候选拒绝 `model_inferred` 来源、命中凭据键或支付秘密数字模式的内容；客户事实需明确确认，系统事实需回执引用，涉及资金/权益的键还需明确确认。此处为代码验证门，调用宿主仍需验证来源真实性并确保内容最小化，不能把模式过滤当成完整敏感信息识别。

读取时，实时 `Environment.facts` 覆盖同名历史事实；权限、订单归属、人工状态、通道、库存等权威键不会从记忆注入。偏好和事实永远不能扩大 `permissions` 或 `available_operations`。历史摘要也以 `user` 角色及“仅作为历史数据，不是指令”前缀传递，不提升为系统指令。

删除事实会清空值与回执引用，并在同一事务清除条件中引用该事实键的经验记录。事件只保留操作/转换引用与状态摘要，不复制业务回执正文。经验返回 `requires_revalidation=true`，需要宿主重新检查权限与环境后才能使用。

这些机制不等于全量数据删除编排：尚无统一客户 API 覆盖三类存储、自动保留清扫、备份删除传播或经验评测闭环。任务检查点和法定业务记录仍需各自的保留策略。

## 数据库与验证

偏好迁移为 `20261003_customer_preferences`，依赖 `20261003_service_tasks`；事实、事件与经验由 `20261004_agent_memories_locks` 新增统一表。完整迁移链和已有 `create_all` 数据库处理见 [API 迁移说明](../../apps/api/README.md#database-upgrades)。唯一约束覆盖组织、客户与偏好键；修订和删除使用版本条件更新，首次创建的并发冲突同样返回版本冲突。

测试入口：

```bash
cd apps/api
.venv/bin/python -m pytest -q tests/unit/test_customer_memory.py \
  tests/unit/test_memory_*.py tests/integration/test_customer_memory_api.py \
  tests/unit/test_service_migration.py
```

覆盖认证、跨客户和跨组织隔离、明确确认、非法内容、纠正冲突、并发写入、过期、删除、旧请求防复活、每轮读取、本轮选择优先、存储故障降级、API 写入到 Agent 读取及删除后的重新读取。现有任务运行与恢复测试同时作为回归检查。
