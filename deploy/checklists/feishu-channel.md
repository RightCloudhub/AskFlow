# 飞书机器人通道（PRD E7b）

## 环境变量

| 变量 | 说明 |
|------|------|
| `FEISHU_VERIFICATION_TOKEN` | 事件订阅 Verification Token（生产必填） |
| `FEISHU_APP_ID` | 应用 App ID（出站回复） |
| `FEISHU_APP_SECRET` | 应用 Secret（出站回复） |

未配置 App ID/Secret 时：仍跑完整 Agent 流水线，响应体带 `reply_text` 供联调；不调飞书开放平台。

## 订阅地址

```
POST {API_BASE}/api/v1/channels/feishu/events
```

1. 飞书后台 → 事件订阅 → 请求网址填上述 URL  
2. 通过 URL 校验（challenge）  
3. 订阅 `im.message.receive_v1`（接收消息）  
4. 机器人权限：接收消息、发送消息（若需主动回复）

## 行为

- 按 `open_id` JIT 访客用户 + 会话  
- `ChatService.handle_user_message` 同主站  
- 审计：`feishu.message`  
- 有 `message_id` 且配置 App 凭证时调用消息回复 API  

## 自检

```bash
curl -s -X POST localhost:8000/api/v1/channels/feishu/events \
  -H 'Content-Type: application/json' \
  -d '{"type":"url_verification","challenge":"x","token":"..."}'
```
