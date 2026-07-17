# 试点接入检查清单 — OIDC + Webhook + 连接器

> 从「代码就绪」到「可试点」。配套 PRD §12.2、STATUS 生产接入项。

## 1. 环境变量契约

| 变量 | 必填 | 说明 |
|------|:----:|------|
| `ASKFLOW_ENV` | 是 | 试点/生产设 `staging` 或 `production`（禁默认 SECRET） |
| `SECRET_KEY` | 是 | ≥16 字符强密钥 |
| `OIDC_ISSUER` | SSO | IdP issuer，如 `https://login.microsoftonline.com/{tenant}/v2.0` |
| `OIDC_CLIENT_ID` | SSO | 应用 client_id，作 ID token `aud` |
| `OIDC_MOCK` | 否 | 生产必须 `0`/未设；仅 dev/test 可用 mock token |
| `DISABLE_LOCAL_REGISTER` | 建议 | 强制走 SSO 时设 `1` |
| `NOTIFY_WEBHOOK_URL` | 离线通知 | HTTPS 接收端；未设则仅内存 sink + DB log |
| `NOTIFY_WEBHOOK_SECRET` | 建议 | HMAC 密钥；默认回退 `SECRET_KEY` |
| 连接器 `base_url` | 业务 | Admin「连接器」页配置订单/CRM 内网 URL |

## 2. OIDC 验收

1. 配置 `OIDC_ISSUER` + `OIDC_CLIENT_ID`，`OIDC_MOCK` 关闭，`ASKFLOW_ENV` 非 test/development。  
2. 前端或联调工具用真实 IdP 签发的 **ID token** 调 `POST /api/v1/admin/sso/oidc/login`。  
3. 期望：200 + access_token；用户 JIT 创建；角色按 `roles`/`groups` 映射（admin/agent/user）。  
4. 坏签名 / 过期 / 错误 `aud` → 4xx，不得发本地 JWT。

## 3. 出站 Webhook 契约

### 请求

- Method: `POST`
- Headers:
  - `Content-Type: application/json`
  - `X-AskFlow-Timestamp`: Unix 秒字符串
  - `X-AskFlow-Signature`: `hex(HMAC-SHA256(secret, timestamp + "." + raw_body))`
- Body:

```json
{
  "event": "sla.breached",
  "ts": 1710000000,
  "data": { "ticket_id": "...", "previous": "warning", "current": "breached", "reason": "first_response" }
}
```

### 联调

- Admin: `POST /api/v1/admin/notify/test-emit` body `{"event":"pilot.test","payload":{}}`
- 查看: `GET /api/v1/admin/notify/logs`
- SLA 扫描会 `emit_safe`：`POST /api/v1/admin/sla/scan`（失败不阻断扫描响应）

### 校验伪代码（接收方）

```
expected = HMAC_SHA256(secret, timestamp + "." + raw_body)
constant_time_compare(expected, header_signature)
reject if |now - timestamp| > 300s
```

## 4. 连接器（≥2）

| name | 用途 | 配置点 |
|------|------|--------|
| `order_status` | 订单状态 | Admin 连接器页 / `PUT /api/v1/admin/connectors/order_status` |
| `crm_lookup` | CRM 账户 | 同上 |

- 试调用: `POST /api/v1/admin/connectors/{name}/invoke` `{"params":{"order_id":"..."}}`
- 上游 4xx/5xx/超时 → `status=mock`、`data_source=mock`（主流程可降级，勿当真数据）

## 5. 试点最小路径

1. Compose/单机起 API + Web；`SECRET_KEY` 与 env 正确。  
2. SSO 或本地 admin 登录。  
3. 配置两个连接器 base_url 并试调用。  
4. 配置 `NOTIFY_WEBHOOK_URL`，test-emit + SLA scan。  
5. 跑 `pytest` + `evals/runners/run_eval.py`（或 GitHub Actions `ci` workflow）。  
6. （可选）打开 `/widget` 或 `public/embed-snippet.html` 验证访客通道。  
7. （可选）`GET /api/v1/admin/audit-logs/export-siem` 或配置 `SIEM_WEBHOOK_URL` 后 `POST .../export-siem`。  
8. （可选）飞书：见 `deploy/checklists/feishu-channel.md`。  
9. （可选）Admin「质检」页查看 refuse/thumbs 与低分 runs。
