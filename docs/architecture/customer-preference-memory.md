# 客户偏好记忆：接口与使用边界

对应 [客服 Agent 方案](../prd/customer-service-agent.md) 的客户事实与偏好生命周期。本阶段支持客户明确确认的有限偏好，不支持自动提取自由文本事实或经验学习。

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

新运行时已接入该读取步骤；旧聊天流水线尚未使用这些偏好，业务策略也需明确实现相应的语言或渠道选择，不能仅凭保存成功声称回复行为已经改变。

偏好没有缓存，也不由运行时复制到任务检查点。删除清空主表的值，保留不含偏好内容的版本标记，防止持有旧版本的请求重新创建内容。业务策略不得将偏好原值重新缓存为事实或写进持久化决策摘要；若扩展其他副本，必须接入统一删除机制。

到期记录立即停止影响决策；当前没有定时物理清理任务。备份恢复流程仍需独立处理删除记录与恢复后的保留规则，本阶段不保证任意旧备份恢复后的删除一致性。

偏好是可选上下文。读取超时、数据库不可用或存储内容校验失败时，运行时保留本轮明确选择并将 `preference_status` 设为 `unavailable`，继续正常任务；诊断日志只记录错误类型。偏好 API 的写入失败不会被伪装成保存成功。订单等实时事实仍需查询业务系统。

## 数据库与验证

新增迁移 `20261003_customer_preferences`，依赖 `20261003_service_tasks`。在项目环境中运行 `python -m alembic upgrade head`。唯一约束覆盖组织、客户与偏好键；修订和删除使用版本条件更新，首次创建的并发冲突同样返回版本冲突。

测试入口：

```bash
cd apps/api
.venv/bin/python -m pytest tests/unit/test_customer_memory.py tests/integration/test_customer_memory_api.py tests/unit/test_service_migration.py -q
```

覆盖认证、跨客户和跨组织隔离、明确确认、非法内容、纠正冲突、并发写入、过期、删除、旧请求防复活、每轮读取、本轮选择优先、存储故障降级、API 写入到 Agent 读取及删除后的重新读取。现有任务运行与恢复测试同时作为回归检查。
