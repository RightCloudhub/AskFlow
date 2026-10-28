# API 清单与统一契约

状态：M0 草案。公开业务前缀 `/api/v1/mall`，后台 `/api/v1/admin/mall`，基础设施 `/api/v1/admin/infra`；内部 lookup 无 API 前缀。关插件对应路由 404。运行时 OpenAPI 为代码契约，草案见 [openapi.yaml](./openapi.yaml)。

## 通用规则

写接口要求 Idempotency-Key 或天然业务唯一键。键绑定认证主体+HTTP方法+路由+规范化请求哈希，首次结果持久化；同 key 改参数409；并发 pending 等待有界，超时409+Retry-After。客户端金额只用于展示，服务重新计价。验证码发送/登录/refresh 有额外防刷与重放约束，不允许以幂等绕过限流或 family revocation。

资源查询强制 owner 过滤，他人/不存在均404；后台需要权限。列表 `{items,next_cursor}`，以 owner+id 或 created_at+id 签名游标，不使用 OFFSET。所有时间 ISO8601 UTC；所有金额严格整数分+currency。模型接口拒绝未知字段，金额/数量/文本边界 Pydantic 校验。

错误 `{code,message,trace_id}`，状态 400/401/403/404/409/422/429/503；已沿用 trace_id。业务码包括 invalid_credentials、verification_invalid、step_up_required、state_conflict、insufficient_stock、insufficient_balance、idempotency_conflict、callback_invalid、amount_mismatch、permission_denied、capability_unavailable。不将完整异常/手机号/订单归属返回给客户。

refresh 推荐 HttpOnly/Secure/SameSite=Strict cookie，限定 `/api/v1/mall/account`；双提交 CSRF token+Origin 校验，CSRF 与 token 轮换；移动/服务客户端可受控返回 body refresh，不在浏览器 localStorage 保存长期 refresh。短期 access 与既有 JWT 兼容并增加 jti/sid/type。

## 用户账号

| 方法 / account 后缀 | 功能与权限 |
|---|---|
| POST /verification/send | 邮箱/手机号、purpose；统一“已受理”；dev/test 受限测试收件箱，生产无验证码回显 |
| POST /verification/verify | challenge_id/code；一次消费，验证凭据用途和目标绑定 |
| POST /register | username+password+已验证 email/phone；MALL_PUBLIC_REGISTER/local_register_allowed；仅 user |
| POST /login | 用户名/邮箱/手机+password 或短信验证凭据，开启 MFA 必须 TOTP/恢复码 |
| POST /oidc-session | 复用已验证 OIDC 登录结果，检查安全策略并建立商城会话 |
| POST /refresh | 随机不透明 token 轮换；旧 token 重放吊销 family，401 |
| POST /logout | jti 吊销至 exp；refresh session 吊销 |
| GET /sessions | 本人设备/最近活跃/IP遮罩，无 refresh 哈希或 token |
| DELETE /sessions/{id} | 本人单设备下线；幂等 |
| POST /sessions/revoke-all | 本人全部下线 |
| POST /password/forgot | 账号存在与不存在统一响应，发送一次凭据 |
| POST /password/reset | 重置凭据+新密码；消费即失效、吊销全部会话 |
| POST /password/change | 旧密码+新密码+step-up；同样吊销 |
| POST /mfa/setup | 本人 recent login；只显示一次 provisioning secret，DB 静态加密 |
| POST /mfa/enable | 校验 TOTP 后启用，返回一次10个恢复码 |
| POST /mfa/disable | 已启用时需 TOTP/recovery + recent step-up |
| POST /step-up | 用途+TOTP/短信/email challenge；签发短时用途绑定凭据 |
| GET /profile / PATCH /profile | 昵称/地区/locale/头像，不直接修改已验证绑定 |
| POST /avatar | 类型白名单+magic header+MAX_UPLOAD_BYTES，经对象端口 |
| POST /bindings/change | 旧目标和新目标各自验证，phone/email 不可仅验证新目标 |
| GET/POST /addresses | 本人地址游标列表/新增 |
| PATCH/DELETE /addresses/{id} | owner+version；默认地址原子更新 |
| GET /export / POST /close | 复用客服导出/删除；关闭前检查在办订单/钱包、脱敏保留财务 |

## 商品、库存、订单

| 方法 / mall 后缀 | 功能 |
|---|---|
| GET /features | 公开最小 features 列表，无管理/依赖细节，供未登录 /shop 发现 |
| GET /catalog/categories | 上架类目树 |
| GET /catalog/products | 关键词、category、min/max cents、sort、cursor；search 端口可降级 |
| GET /catalog/products/{id} | SPU/SKU/当前价格，缓存详情；inactive 不提供购买 |
| GET /inventory/{sku_id} | 用户可见库存摘要，不泄露预占人 |
| GET /inventory/flash-sales | 有效活动和限购 |
| POST /inventory/flash-sales/{id}/purchase | 一次请求 token+限流+key；full 返回202 queue_id，lite 同步下单 |
| GET /inventory/flash-requests/{id} | 本人 queued/succeeded/rejected 和订单引用 |
| GET /cart | 本人落库购物车，实时价格/库存摘要 |
| PUT/DELETE /cart/items/{sku_id} | 本人数量校验/删除，server 不接受 price |
| POST /cart/merge | 可选游客 SKU/qty 合并，全部主库验证 |
| POST /orders/quote | SKU/qty/address/wallet_cents → server total+一次 checkout_token |
| POST /orders | checkout_token、items、address、key；统一事务预占，201 |
| GET /orders / GET /orders/{id} | 本人按 status 游标/详情，PII 遮罩规则 |
| POST /orders/{id}/cancel | Gateway prepare/execute，L2+确认；pending 取消释放，paid 走退款 |
| GET /orders/{id}/logistics | mock 明确 data_source，不伪造真实物流 |
| POST /orders/{id}/received | SHIPPED→DELIVERED；本人确认收货 |
| POST /orders/{id}/refunds | partial/full，金额上限 server 校验，Gateway L2+确认+审批 |
| GET /refunds / GET /refunds/{id} | 本人受理、审批、到账状态区分 |

## 支付、钱包、邀请、消息

| 方法 / mall 后缀 | 功能 |
|---|---|
| POST /payments | order_id、method=wallet/mock/mixed；amount server 推导；大额 step-up |
| GET /payments/{id} | 本人支付状态，mock 付款页面参数 |
| POST /payments/{id}/mock-confirm | dev/demo sandbox 签名确认入口；不能以客户输入伪造到账金额 |
| POST /payments/callbacks/mock | 无用户 JWT，HMAC+时间窗+流水唯一+金额/币种比对 |
| GET /wallet / GET /wallet/journals | 本人可用/冻结余额、currency、游标流水 |
| GET /wallet/journals/{id} | owner 过滤业务引用与用户分录，无其他客户账户 |
| POST /wallet/topups | amount/currency+key；生成 topup 与支付单；确认后记账 |
| GET /wallet/topups | 本人充值状态 |
| GET /referrals/code | 本人邀请码/链接；天然 user 唯一 |
| POST /referrals/bind | 注册验证后绑定一次；不可自邀/循环，device/IP 哈希信号 |
| GET /referrals/rewards | 本人 pending/review/paid/reversed/receivable，游标 |
| GET /notifications / GET /notifications/unread | 站内信列表/未读；带客户归属 |
| POST /notifications/{id}/read | 本人幂等读标记 |
| GET/PUT /notifications/preferences | event×channel、频率/静默窗口 |
| POST /support/conversations | order/refund/journal_id；验证归属后创建 AskFlow 上下文 |
| GET /support/messages | 本人站内信+会话+工单引用统一入口 |
| POST /support/tickets / POST /support/handoff | 复用 Gateway 及既有 service，不自建客服工单系统 |
| POST /actions/prepare / POST /actions/execute | allowlisted mall.*；认证 scope 派生，确认 token 绑定参数和能力 |

## 管理后台

| 方法 / admin/mall 后缀 | 权限与要求 |
|---|---|
| GET /permissions | 当前有效权限；旧 admin 可映射超管，授予需审计 |
| GET/POST /roles / PUT /roles/{id}/permissions | user:manage；不能给自己绕过审批的财务权限 |
| PUT /users/{id}/roles / POST /users/{id}/disable | user:manage；全会话吊销；禁用审计 |
| POST /users/{id}/mfa-reset | user:manage，审批人不同；不直接泄露 TOTP |
| POST/PATCH /catalog/categories、/catalog/products、/catalog/skus | catalog:write；version，价格和上架事件 |
| POST /inventory/{sku_id}/adjust | inventory:write；qty+reason+version，不能使库存负数 |
| POST/PATCH /inventory/flash-sales | inventory:write；限购/价格/库存阈值配置 |
| GET /orders / POST /orders/{id}/ship、/complete | order:read/write；状态表/CAS/审计/事件 |
| GET /refunds / POST /refunds/{id}/approve、/reject | order:refund；持久审批，不允许客户请求设置 approval_actor |
| GET /wallet/accounts、/wallet/journals | wallet:read；PII 最小化 |
| POST /wallet/adjustments / POST /wallet/adjustments/{id}/approve | wallet:adjust / wallet:approve；双人复核、step-up、版本 |
| POST /finance/reconcile / GET /finance/runs、/finance/diffs | finance:reconcile/read；手动报告和差异 |
| POST /finance/diffs/{id}/resolve | finance:reconcile；引用批准冲正或重建记录，不能删除差异 |
| GET /referrals/risks / POST /referrals/risks/{id}/review | risk:review；决定和备注审计 |
| GET/POST /notifications/templates / GET /notifications/deliveries | notify:write/read；模板版本/多语言/投递记录 |
| GET/PUT /settings/{key} / POST /settings/{key}/rollback | settings:read/write；白名单 typed 值，expected_version；rollback 新版本 |
| GET /dashboard | operations:read 或 finance:read；GMV/转化/退款/余额/工单/风控 |
| GET /support/orders/{id}/snapshot | support:read；权限及工单关联范围，PII 遮罩 |

## 内部契约

`GET /internal/mall/orders/lookup?order_id=&customer_id=`：非空 ORDER_LOOKUP_TOKEN 的 bearer 验证；200 `{order_id,customer_id,status}`，status 使用小写具体数据库状态；404 不暴露存在性。mall_order 启用且无 URL 时 scoped adapter 自动本地调用；原 URL 配置始终优先。

Agent 能力 mall.order.get、mall.logistics.get、mall.wallet.balance 为 read/L1；mall.order.cancel 为 irreversible/L2/确认；mall.refund.submit 和 refund.submit 为 irreversible/L2/确认/超限审批。参数只能包含资源标识/理由/明确退款金额，owner 与权限由可信执行上下文注入。
