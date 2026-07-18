# 企微 / 钉钉通道接入清单

## 企微 WeCom

| 变量 | 说明 |
|------|------|
| `WECOM_TOKEN` | URL 校验 / 回调 token（生产必配） |
| `WECOM_CORP_ID` | 企业 ID（出站回复扩展用） |
| `WECOM_AGENT_ID` | 应用 AgentId |

- 回调：`POST/GET /api/v1/channels/wecom/events`
- GET 带 `echostr` + `msg_signature` 做 URL 验证
- 文本 `MsgType=text`；图片/文件转 `[attachment ...]` cue

## 钉钉 DingTalk

| 变量 | 说明 |
|------|------|
| `DINGTALK_APP_SECRET` | 签名密钥（生产必配） |
| `DINGTALK_APP_KEY` | 应用 key（扩展用） |

- 回调：`POST /api/v1/channels/dingtalk/events`
- Header `timestamp` + `sign` HMAC-SHA256
- 返回机器人 `{msgtype:text, text:{content}}`

## 通用

- 与飞书相同：`ensure_channel_user` + `ChatService` 流水线
- Profile：`full` 默认启用 `wecom` / `dingtalk` 插件
- 开发：`ASKFLOW_ENV=development` 时未配密钥可本地联调
