# 服务运营

[配置指南](README.md) · 下一篇：[渠道与扩展](channels.md)

这些设置控制知识答案之外的工作：订单查询、已保存任务、客服队列、服务时间检查和通知。

## 配置已保存的服务任务

服务任务是保存在后台 worker 中并可继续执行的请求。其记录存储在数据库中；此调度器不需要 Redis。

```dotenv
SERVICE_TASKS_ENABLED=true
SERVICE_TASKS_GOALS=order_status
SERVICE_TASK_POLL_SECONDS=5
```

还必须启用 `agent` 功能。API 在测试模式之外会自动启动 worker。轮询间隔以秒为单位，且必须至少为 `1`；它是扫描间隔，不是保证的客户响应时间。

| 目标 | 当前含义 |
| --- | --- |
| `order_status` | 检查已认证客户的订单；默认启用 |
| `ticket_resolution` | 登记工单；需选择启用，且完成仅验证已登记 |
| `human_handoff` | 安排转人工；需选择启用，并有单独的客服受理集成 |

接受别名 `order`、`ticket` 和 `handoff`，但为清晰起见请使用完整名称。例如：

```dotenv
SERVICE_TASKS_GOALS=order_status,ticket_resolution,human_handoff
```

同时启用相应的 ticket/handoff 功能。通知和退款适配器不在默认的 worker 策略注册表中；将此列表中添加 `notification`、`refund_request`、`notify` 或 `refund` 不会创建可用的退款或通知工作流。

要停止接受新的已保存目标，同时让 worker 仍可用于现有工作，请使用空列表：

```dotenv
SERVICE_TASKS_GOALS=
```

要停止此任务接收和 worker，请设置 `SERVICE_TASKS_ENABLED=false` 并重启。这两种情况都会在适用时将未处理的请求留在现有的消息管道上；它们不一定禁用所有同步订单工具或工单/转人工行为。这两种更改都不会取消现有记录或撤销已发出的外部操作。

## 连接订单查询

请业务系统所有者提供一个能够理解 AskFlow 已认证客户身份的端点。仅凭订单号并不能证明调用方拥有该订单。

```dotenv
ORDER_LOOKUP_URL=https://orders.example.com/askflow/order-status
ORDER_LOOKUP_TOKEN=REPLACE_WITH_ORDER_SERVICE_TOKEN
```

这是**完整的端点 URL**；与模型基础地址不同，它不会自动获得 `/v1` 后缀。如果端点被有意配置为无 bearer 认证，则令牌是可选的。否则请提供实际的服务令牌。

当前已保存任务适配器发送带有查询参数 `order_id` 和 `customer_id` 的 HTTP GET，并在配置时发送 `Authorization: Bearer ...`。服务必须验证客户/订单关系，并返回扁平 JSON，例如：

```json
{
  "order_id": "ORD202401019999",
  "customer_id": "REPLACE_WITH_AUTHENTICATED_ASKFLOW_USER_ID",
  "status": "shipped"
}
```

这些是示例值；真实响应必须包含所请求的订单和已认证客户 ID。不要构建一个仅回显任意客户 ID 而不验证所有权的服务。状态必须具体；缺失、mock、未知或不匹配的数据都不能使任务解决。

订单适配器当前有固定的五秒 HTTP 超时。`LLM_TIMEOUT_SECONDS` 和连接器记录的 `timeout_ms` 不会更改它。较旧的同步订单工具有不同的响应解释；请验证你的部署实际使用的路径。

重启后，用客户账号测试一个有效订单、一个属于其他客户的订单，以及一个不可用的上游服务。刷新会话以阅读已保存的后台结果。当前 UI 没有任务看板或取消按钮，后台更新也不保证以实时对话推送的方式到达。

## 配置人工支持

启用 `handoff` 并安排客服角色。如果需要，添加 `teams` 功能，然后使用 **Admin → 技能组 (Skill groups)** 创建组并添加客服。没有适当组成员资格的 agent 看不到新入队的请求。`mvp` 包不包含 `teams`；使用客服范围队列时请添加 `+teams`。

```dotenv
HANDOFF_TIMEOUT_SECONDS=300
SWEEPER_ENABLED=true
SWEEPER_INTERVAL_SECONDS=60
```

超过超时时间的无人认领队列条目可以变成高优先级工单，并将会话退回自动处理。sweeper 定期检查，因此该事件可能刚好在阈值之后发生。其有效间隔至少为 15 秒。已被认领的条目不会被无人认领队列扫描超时处理。

`SWEEPER_ENABLED` 同时控制定期转人工超时扫描和 SLA 扫描。它不控制服务任务或索引 worker。后台作业在 `ASKFLOW_ENV=test` 中被禁用。

通过从测试客户账号请求人工、以客服身份认领并回复、然后单独测试一个有意无人认领的请求来验证。界面说明请使用 [客服人员](../user-guide/support-staff.md)。

## 理解 SLA 策略

当前的服务时间策略内置于应用程序中，不是可编辑的环境设置或浏览器表单：

| 工单优先级 | 首次响应目标 | 解决目标 |
| --- | --- | --- |
| `urgent` | 15 分钟 | 120 分钟 |
| `high` | 30 分钟 | 240 分钟 |
| `medium` | 120 分钟 | 1,440 分钟（1 天） |
| `low` | 480 分钟 | 4,320 分钟（3 天） |

警告大约从相关时长的 70% 开始。这些是从工单创建起算的经过时间目标，不是营业时间日历。未知优先级使用 medium 策略。策略自定义需要开发者/集成更改；诸如 `SLA_TIMEOUT` 的变量将被忽略。

使用 **Admin → SLA 监控 → 立即扫描并通知 (Scan and notify now)** 执行手动检查。它可以发出通知；它不只是刷新显示。解释结果请参见 [监控指南](../user-guide/reports.md)。

## 连接通知

**Webhook** 是 AskFlow 向其发送事件的 HTTP 地址。它需要一个接收应用；电子邮件地址不是 webhook URL。

```dotenv
NOTIFY_WEBHOOK_URL=https://automation.example.com/askflow/events
NOTIFY_WEBHOOK_SECRET=REPLACE_WITH_A_SHARED_NOTIFICATION_SECRET
```

在需要其路由或效果的地方启用 `notify` 功能。接收方和 AskFlow 必须就密钥达成一致。当省略单独密钥时，签名回退到 `SECRET_KEY`。

事件包括工单创建、转人工超时，以及由相关路径发出的 SLA 预警/违约。请求体包含 `event`、`ts` 和 `data`。对于接收方的开发者，签名是对 `timestamp + "." + raw_body` 计算的十六进制 HMAC-SHA256，通过 `X-AskFlow-Signature` 提供；时间戳也在 `X-AskFlow-Timestamp` 中。

没有 URL 时，事件会记录到进程内接收器，并可能记录为 `sent_sink`；没有发生电子邮件或外部送达。有 URL 时，请测试一个预期事件并在目的地确认接收。Webhook 送达失败不一定会使客户的对话请求失败。

这些设置不暴露 SMTP 配置或通用的客户“发送电子邮件”自动化。要送达电子邮件或即时通讯通知，接收集成必须实现它。已保存的电子邮件偏好不会配置该送达。

## 管理基于数据库的连接器

**Admin → 业务连接器 (Business connectors)** 显示连接器记录和一个测试操作。这些记录独立于 `ORDER_LOOKUP_URL`；更改名为 `order_status` 的记录不会配置已保存任务的订单适配器。

初始的 `order_status` 和 `crm_lookup` 记录指向一个公共 HTTP echo 服务用于演示。不要像对待你的业务系统那样向它们发送真实客户信息。

没有连接器编辑表单。经授权的管理员/集成可以使用带有完整配置体的 `PUT /api/v1/admin/connectors/{name}`。供运维人员调整的示例：

```json
{
  "name": "crm_lookup",
  "base_url": "https://crm.example.com",
  "method": "GET",
  "path_template": "/customers/{customer_id}",
  "auth_header": "Bearer REPLACE_WITH_CRM_TOKEN",
  "timeout_ms": 5000,
  "enabled": true,
  "description": "Customer lookup",
  "headers": {}
}
```

`timeout_ms` 是毫秒（5000 = 五秒）。`auth_header` 是完整的 Authorization 头值。此更新不是部分补丁：省略的字段可能会重置为默认值，包括认证和头。更改一个字段时请保留完整的预期配置。

通过 `POST /api/v1/admin/connectors/crm_lookup/invoke` 测试，请求体为 `{"params":{"customer_id":"APPROVED_TEST_CUSTOMER_ID"}}`。当前通用连接器会替换路径占位符，并在 URL 查询中发送参数，即使对于 GET 以外的方法也是如此；它不是通用的 JSON 请求体工作流构建器。浏览器中的 **试调用 (Test call)** 发送空参数。

检查 `status` 和 `data_source`：失败可能返回 mock 响应而不是抛出错误。成功注册或 echo 响应不会将此记录连接到任意对话意图。请让运维人员安排任何所需的工作流集成。

## 当没有界面时使用管理员 API

API 是一种直接向 AskFlow 发送结构化请求的方式。如果你不熟悉它，请将上面的端点和必填字段交给你的运维人员。你不需要编造包含机密令牌的终端命令。

对于本地开发安装，`http://localhost:8000/docs` 的交互式界面提供了一个表单：

1. 找到本地登录操作 `POST /api/v1/admin/auth/login`，并选择 **Try it out**。
2. 在请求表单中输入你的管理员用户名和密码，并私下执行它。
3. 只将返回的 `access_token` 复制到页面的 **Authorize** bearer 令牌字段，然后授权。
4. 找到所需操作，提供其路径字段和请求体，检查它们，并执行一次。
5. 检查响应和相关已保存记录。完成后退出授权对话框。

交互式操作会真正执行：连接器调用可能联系外部系统，更新会更改已存储的配置。检查连接时请使用已批准的测试记录。将令牌响应排除在截图和支持报告之外。

交互式文档在 staging/production 中被禁用。在那里请使用你组织批准的管理员 API 客户端；不要仅仅为了暴露该表单而将共享的生产安装切换为 development。

## 响应规则、预算和偏好

关于 [管理](../user-guide/administration.md) 中描述的基于数据库的控件，请使用 **意图路由 (Intent routing)** 和 **提示词模板 (Prompt templates)**。已启用的已保存目标可以在旧版意图映射之前被受理，并且当前答案路径并不普遍使用已存储的提示词模板。保存模板不能凌驾于授权之上，也不能保证每个路径中的措辞都发生变化。

`MAX_LOOP_STEPS`、`MAX_TOOL_CALLS`、`MAX_WALL_MS` 和 `MAX_RETRIES_PER_TOOL` 约束较旧的工具循环。它们不是已保存任务调度器的完整预算。在此版本中，任务期限/成本预算和偏好保留不是全局环境设置。偏好请求明确选择保留期（默认 30 天，范围 1–90）；请参见 [隐私](../user-guide/privacy.md)。
