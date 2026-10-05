# 渠道与扩展

[配置指南](README.md) · 下一篇：[验证与故障排查](troubleshooting.md)

渠道设置既需要 AskFlow 配置，也需要外部网站或即时通讯平台的配置。加载插件只是该设置的一部分。

## 网站微件

启用 `widget`，重启 API，并让网站运维人员提供 Web 路由 `/widget`，同时确保 `/api` 代理正常工作。给网站所有者的一个简单嵌入示例如下：

```html
<iframe
  src="https://support.example.com/widget"
  title="Customer support"
  width="400"
  height="600"
></iframe>
```

将示例地址替换为实际的 AskFlow 网站。这是用于宿主网站的 HTML，不是要粘贴到 `.env` 中的设置。宿主必须允许该 frame，并且 AskFlow 的响应头必须允许预期的嵌入。请在访问者使用的浏览器中进行测试。

没有用于品牌、允许的宿主站点、会话过期或欢迎文本的 `WIDGET_*` 环境设置。当前访客会话使用固定的两小时访客令牌和浏览器标签页会话存储。其记录的 `origin` 字段不是强制的主机允许列表；CORS 不能替代允许列表。

验证匿名访客可以打开微件、提出受支持的问题，并在同一会话中重新加载对话。微件访客不会自动链接到普通网站账号。后续送达、身份验证、品牌更改和过期会话恢复可能需要额外的集成。

## 飞书

请飞书应用所有者提供事件验证令牌、应用 ID 和应用密钥。启用 `feishu` 并添加：

```dotenv
FEISHU_VERIFICATION_TOKEN=REPLACE_WITH_FEISHU_VERIFICATION_TOKEN
FEISHU_APP_ID=REPLACE_WITH_FEISHU_APP_ID
FEISHU_APP_SECRET=REPLACE_WITH_FEISHU_APP_SECRET
```

1. 重启 AskFlow。
2. 在飞书应用的事件设置中，使用你实际的、外部可访问的 HTTPS 地址加上 `/api/v1/channels/feishu/events`。
3. 完成平台的 URL 挑战验证。
4. 订阅 `im.message.receive_v1` 并授予相关的接收/回复权限。
5. 通过实际的机器人发送一个文本问题，并在飞书中验证回复。

应用 ID 和密钥是出站 API 回复所需的。没有它们，开发处理可能会在回调响应中产生 `reply_text`，但飞书中没有消息。文本是已实现的输入路径；不要仅仅因为 URL 验证通过就假设支持加密事件信封、附件或任意平台模式。请让平台运维人员根据适配器验证所选模式。

运维人员的请求详情请使用 [飞书集成检查清单](../../deploy/checklists/feishu-channel.md)。

## 企业微信

启用 `wecom` 并获取其管理员提供的应用详情：

```dotenv
WECOM_TOKEN=REPLACE_WITH_WECOM_CALLBACK_TOKEN
WECOM_CORP_ID=REPLACE_WITH_CORPORATION_ID
WECOM_AGENT_ID=REPLACE_WITH_APPLICATION_ID
```

该适配器暴露 GET/POST `/api/v1/channels/wecom/events`。它当前接受简化的 JSON 文本事件和普通/测试 URL 验证。它不是完整的企业微信加密 XML 应用回调集成。

特别地，设置 `WECOM_TOKEN` 并不会为每个 POST 提供完整的入站认证：当前消息处理器在类生产模式中仅比较可选的请求体令牌。运维人员必须提供经过验证的网关处理，或完成适配器，然后才能将其作为受信任的生产消息源暴露。

`WECOM_CORP_ID` 和 `WECOM_AGENT_ID` 保留用于扩展，当前不用于发送消息。该实现不提供可用的企业微信出站回复客户端，生产回调响应也不包含开发用的 `reply_text` 字段。仅这些环境值无法完成双向支持机器人。

请与平台所有者安排兼容的网关/适配器，验证身份和回复送达，然后与客户分享该渠道。请参见 [企业微信/钉钉检查清单](../../deploy/checklists/wecom-dingtalk-channel.md)。

## 钉钉

启用 `dingtalk` 并配置：

```dotenv
DINGTALK_APP_SECRET=REPLACE_WITH_DINGTALK_SIGNATURE_SECRET
DINGTALK_APP_KEY=REPLACE_WITH_DINGTALK_APPLICATION_KEY
```

该适配器接受 POST `/api/v1/channels/dingtalk/events`，为其支持的消息处理验证 `timestamp`/`sign` 头格式，并返回文本机器人响应体。`DINGTALK_APP_KEY` 保留且当前不用于建立出站客户端。

平台运维人员必须确认回调模式与此签名和响应格式匹配。该适配器不是钉钉流式、加密回调或异步回复的通用实现；时间戳新鲜度/重放处理也需要在实际网关中评估。成功的挑战响应并不能证明经过认证的消息处理。

测试一条真实的文本消息、一个被拒绝的无效签名，以及可见的响应送达。使用上面链接的集成检查清单。附件线索可以记录文件或图片的存在，而不会提取其内容。

## 分别验证后续更新

所有渠道都需要对初始回复、人工回复和后台任务结果进行独立测试。当前渠道适配器不保证每条后续客服消息或任务更新的出站送达。在没有你自己经过验证的集成的情况下，不要宣传完整的跨渠道延续或自动账号合并。

如果你不使用某个渠道，请从所选 profile/增量中移除其插件，并对齐前端功能列表。仅省略凭据并不等同于禁用其入站路由。

## 语言和机器人 profile

`DEFAULT_LOCALE=zh-CN` 是默认值。小型后端消息目录还有 `en-US`；它不会翻译 React 界面或每条硬编码响应。已保存的客户偏好使用自己的词汇表，包括 `en`，并且是一个单独的功能。

高级集成可以定义机器人 profile：

```dotenv
DEFAULT_LOCALE=en-US
DEFAULT_BOT_ID=support
BOT_PROFILES_JSON='[{"id":"support","name":"Support","system_prompt_key":"rag.system","knowledge_tags":[],"locale":"en-US"}]'
```

JSON 是对象列表。加载器保留一个默认机器人，并在请求的 profile 不存在时回退。格式错误的 JSON 会被静默忽略，而不是必然停止启动，因此请让运维人员在重启后检查机器人端点 `/api/v1/admin/bots`。该管理员端点需要 `ops` 功能。

这些 profile 字段不会建立单独的安全知识集合，也不保证在当前对话管道中全程选择提示词/区域设置。没有完整的多机器人配置界面或客户机器人选择器。请将基于 profile 的行为视为需要逐路径验证的集成。

## MCP、推理和沙箱开关

这里的 **MCP** 暴露一个用于注册已批准工具名称的扩展。要使用已实现的注册支持，请启用 `mcp` 功能并设置 `MCP_ENABLED=true`，同时使用逗号分隔的 `MCP_TOOL_WHITELIST`（默认 `search_knowledge`）。重启并使用管理员账号检查 `/api/v1/admin/mcp/tools`。

此版本中没有远程 MCP 服务器 URL 或传输配置。未知的允许列表名称可能变成 echo 桩，而不是真正的远程工具。启用该开关不会安装外部集成。

`REASONING_ENABLED` 默认为 false。启用时，`REASONING_INTENT_WHITELIST` 选择确切的意图名称，`REASONING_MAX_STEPS` 为较旧的循环添加步骤。默认允许列表 `product_faq,troubleshoot` 与正常的内置意图词汇表不匹配，因此仅启用它可能没有效果。它不是提供商特定的“推理模型”控件。

`SANDBOX_ENABLED` 默认为 false，仅更改以 sandbox 为前缀的工具的门控。它不会创建隔离的执行环境或安装工具。除非开发者已提供并验证了该执行环境，否则请保持它为 false。

## 将审计导出到安全系统

**SIEM** 是收集安全事件的外部系统。如果你的运维人员使用审计导出/推送 API，请将 `SIEM_WEBHOOK_URL` 设置为其已批准的接收集成。仅该值不会启动持续的审计转发。标准配置中没有定期转发作业或单独的 SIEM 认证设置。

请让接收方的运维人员确认请求格式和访问控制，并验证一次明确的导出/推送。集成接口请参见 [审计端点](../../apps/api/app/api/v1/admin/audit_logs/routes.py)。
