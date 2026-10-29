# 商城 API 清单

源码已编写，尚未启动生成 OpenAPI 或验证响应。以下以路由源码为准；M0 草案中的 `/mall/orders`、`/mall/payments` 已收敛到领域前缀。成功响应目前多数为 200，注册为 202。

客户前缀 `/api/v1/mall`，后台 `/api/v1/admin/mall`。身份来自 JWT；客户资源统一 owner 过滤，越权 404。金额为整数分。业务写入使用 `Idempotency-Key`，同 key 异参数 409，TTL 由 Settings 控制。验证码、refresh、MFA 因单次凭据有独立重放语义，不能用“重放成功”绕过刷新家族吊销。

错误为 `{code,message,trace_id}`；版本冲突／非法迁移 409，未认证 401，权限不足 403，限流 429。列表采用 cursor／next_cursor，配置历史使用 before 版本。日期为 UTC ISO 8601。

## 客户接口（相对客户前缀）

| 方法与路径 | 内容 |
|---|---|
| GET `/features`、GET `/files/{key}` | 最小公开插件发现、校验对象名称后读取图片 |
| POST `/account/verification/send`、`/account/verification/verify` | target/channel/purpose → challenge → 一次 proof |
| GET `/account/verification/demo/{id}` | 仅测试或显式开发演示收件箱，生产禁止 |
| POST `/account/register`、`/account/login` | 验证注册；用户名／邮箱／手机密码或验证码登录，MFA |
| POST `/account/oidc-session` | 既有 OIDC 验证和账户绑定，再校验商城 MFA |
| POST `/account/refresh`、`/account/logout` | Cookie+CSRF+Origin；refresh 轮换、注销吊销 |
| POST `/account/password/forgot`、`reset`、`change` | 重置 proof／改密 step-up，成功后吊销会话 |
| GET `/account/sessions`、DELETE `/account/sessions/{id}`、POST `/account/sessions/revoke-all` | 设备会话与下线 |
| POST `/account/step-up`、`/account/mfa/setup`、`enable`、`disable` | 目的绑定令牌，TOTP 与恢复码 |
| GET/PATCH `/account/profile`、POST `/account/avatar` | 昵称地区语言版本、受限图片上传 |
| POST `/account/bindings/change` | old/new proof、channel、step_up_token，旧新目标双验证 |
| GET/POST `/account/addresses`、PATCH/DELETE `/account/addresses/{id}` | 收货地址归属、版本和默认地址；PATCH/DELETE 带 expected_version，所有写入带幂等键 |
| GET `/account/export`、POST `/account/close` | 导出；未完订单／支付和钱包阻注销、脱敏保留引用 |
| GET `/catalog/categories`、`/catalog/search`、`/catalog/products/{id}` | 分类、q/category/min/max/sort/cursor、详情 |
| GET `/inventory/{sku_id}`、`/inventory/flash-sales` | 库存和活动 |
| POST `/inventory/flash-sales/{id}`、GET `/inventory/flash-requests/{id}` | 限购入队／同步下单；queued 不代表成交 |
| GET `/order/cart`、PUT `/order/cart/items`、DELETE `/order/cart/items/{sku_id}` | 持久购物车，SKU+qty |
| POST `/order/checkout`、`/order/orders` | 服务端报价、一次 token、事务预占下单 |
| GET `/order/orders`、`/order/orders/{id}`、`/order/orders/{id}/logistics` | 本人列表／详情／mock 物流 |
| POST `/order/orders/{id}/cancel`、`/order/orders/{id}/refunds` | Gateway L2+确认；超限退款进入 requested 等待运营复核 |
| POST `/order/orders/{id}/received` | 本人确认收货，版本检查、SHIPPED→DELIVERED |
| GET `/order/refunds`、`/order/refunds/{id}` | 本人退款状态 |
| POST `/payment`、GET `/payment/{id}` | mock/wallet/mixed；服务器金额；大额 step_up_token |
| POST `/payment/{id}/mock` | 模拟成功／失败，可关闭 deliver_callback 测试丢回调 |
| POST `/payment/callbacks/mock` | 原始 JSON + X-Payment-Signature HMAC；金额/币种/流水/时间校验 |
| GET `/wallet`、`/wallet/entries`、`/wallet/entries/{id}`；GET/POST `/wallet/topups` | 可用／冻结余额、本人流水与充值历史、充值支付单 |
| POST `/referral/code`、`/referral/bind`、GET `/referral/rewards` | 邀请码、不可变防循环关系、奖励状态 |
| GET `/notify`、POST `/notify/{id}/read`、GET/PUT `/notify/preferences` | 消息与未读数、读标记、渠道／静默偏好 |
| GET/POST `/support` | 会话／工单引用；POST 可携带 order_id/refund_id/wallet_journal_id 及 ticket/handoff |
| GET `/admin/permissions` | 当前权限供界面收敛 |

取消／退款第一次请求不带确认令牌，返回 needs_confirmation 与 token；第二次沿用 key、参数并增加 token。接口和聊天复用同一 Gateway 政策与台账，不暴露任意能力执行器。

## 后台接口（相对后台前缀）

| 方法与路径 | 权限／行为 |
|---|---|
| GET `/account`、POST `/account/{id}/state` | user:manage；停用吊销 |
| GET `/account/mfa-resets`、POST `/account/{id}/mfa-reset`、`/account/mfa-resets/{id}/approve` | user:manage；step-up、两人审批 |
| GET `/catalog`；POST `/catalog/categories`、`products`、`skus` | catalog:write |
| POST `/catalog/images`；GET `/catalog/skus`；PUT `/catalog/products/{id}` | catalog:write；校验并上传图片后返回对象 key，SKU 编号列表，商品版本编辑 |
| PATCH `/catalog/products/{id}/status`、`/catalog/skus/{id}/status`；PUT `/catalog/skus/{id}/price` | catalog:write、版本和变更事件 |
| GET `/inventory`、`/inventory/{sku_id}`；POST `/inventory/{sku_id}/replenish`、`/inventory/flash-sales` | inventory:write |
| GET `/order`；POST `/order/{id}/transition` | order:read/write；发货／送达／完成 |
| GET `/order/refunds/pending`；POST `/order/refunds/{id}/review` | order:refund、approved/expected_version |
| GET `/payment`、`/payment/statement/{day}` | finance:reconcile；mock 日账单 |
| GET `/wallet/accounts`、`/wallet/{user_id}/balance`、`/wallet/adjustments`、`/wallet/reversals` | wallet:read |
| POST `/wallet/adjustments`、`/wallet/adjustments/{id}/approve` | wallet:adjust/approve、双人 step-up |
| POST `/wallet/reversals`、`/wallet/reversals/{id}/approve` | wallet:adjust/approve、只追加冲正 |
| GET/POST `/wallet/reconciliation`；GET `/wallet/reconciliation/{id}/diffs` | finance:reconcile |
| POST `/wallet/differences/{id}/review` | finance:reconcile；保留 expected/actual，记录引用和原因 |
| GET `/referral`；POST `/referral/{id}/review` | risk:review |
| POST `/notify/templates`；GET `/notify/deliveries` | notify:write；纯文本白名单变量 |
| GET `/support` | support:read；不含收货地址的快照 |
| GET/POST `/roles`；POST `/roles/grant`；PUT `/roles/{id}/permissions`；DELETE `/roles/grants/{user_id}/{role_id}` | rbac:write；内置角色权限不可改 |
| GET `/settings`；PUT `/settings/{key}`；GET `/settings/{key}/history`；POST `/settings/{key}/rollback` | settings:write；白名单整数值、版本和审计 |
| GET `/dashboard` | order:read；GMV、转化率／退款率（万分比）；钱包汇总、风控、未结工单分别要求 wallet:read、risk:review、support:read |

额外 GET `/api/v1/admin/infra` 输出能力矩阵；`/health/live` 与 `/health/ready` 区分进程和关键依赖。

## AskFlow 内部契约

GET `/internal/mall/orders/lookup?order_id=&customer_id=` 使用非空 ORDER_LOOKUP_TOKEN bearer 鉴权。响应是既有 README 的扁平状态结构，来源标记 mall_database；归属不符返回 404。mall_order 启用且 ORDER_LOOKUP_URL 为空时走本地 adapter，配置 URL 时沿用 HTTP。

mall.order.get、mall.logistics.get、mall.wallet.balance 为 read/L1；mall.order.cancel、mall.refund.submit、refund.submit 为 irreversible/L2/确认，退款超限需人工。身份只取认证会话，不取自然语言中的 customer_id。

mock 成功模拟器可用 `payer_reference` 提供付款关联测试信号；回调中的 `payer_hash` 为签名覆盖的摘要，不能接收明文支付账户。console 验证码不写日志；只有受限 demo endpoint 可读取开发凭据。

可选游客购物车合并、完整发票、复杂售后和真实支付供应商不在当前路由中，不应照旧草案调用虚构端点。
