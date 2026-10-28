# 商城事件与消费契约

状态：M0 设计。所有事件复用现有 outbox；不直接在请求成功前 publish。信封对齐 arch.md §10.7，tenant_id 固定 deployment，不引入伪多租户。

```json
{
  "event_id": "UUID",
  "event_type": "mall.order.paid",
  "tenant_id": "deployment",
  "occurred_at": "2026-10-29T00:00:00Z",
  "trace_id": "trusted-trace-id",
  "aggregate": {"type": "order", "id": "UUID", "version": 2},
  "payload": {
    "user_id": "authenticated-owner-id",
    "order_id": "UUID",
    "currency": "CNY",
    "amount_cents": 1000
  }
}
```

outbox 行 event_type/aggregate/aggregate_id 与信封一致；event_id 在 emit 时生成，不以每次 relay UUID 重建。信封版本作为额外 schema_version 字段，初始1。不含完整地址、手机号、凭据、验证码、TOTP、任意原始用户输入。面向用户的通知再经模板和 PII 遮罩。

| 事件 | 生产者 | 消费者与效果 |
|---|---|---|
| mall.account.registered/verified/closed | account | notify、安全通知、referral 绑定检查 |
| mall.catalog.changed | catalog | 搜索索引、cache invalidate；按聚合 version 忽略旧索引事件 |
| mall.inventory.changed/insufficient | inventory | 缓存摘要、指标；不足不发外部资金动作 |
| mall.flash.accepted/failed | inventory | 订单 worker/配额补偿、监控 |
| mall.order.created/cancelled/paid/shipped/delivered/completed | order | notify、索引/运营、referral 首单奖励；完成后收入结转 |
| mall.payment.succeeded/failed/late | payment | notify、对账/风险；late 进入退款清算 |
| mall.refund.requested/approved/rejected/settled/unknown | order/payment | notify、referral 撤回、财务差异/人工审核 |
| mall.wallet.posted/frozen/unfrozen | wallet | notify、快照缓存失效、财务指标 |
| mall.topup.succeeded | wallet/payment | notify；记账已在确认事务完成，消费者不重复记钱 |
| mall.referral.pending/paid/reversed/review | referral | notify、风控/运营指标 |
| mall.reconciliation.difference | wallet | 财务角色通知、告警；不自动改账 |
| mall.settings.changed | admin | 每实例缓存版本失效；敏感设置不能包含密钥 |
| ticket.status_changed/support.reply | 既有 ticket/handoff 增量 | support 经 service 获取已验证 link→notify；不广播其他客户消息 |

## 投递与去重

同事务消费：领取 event/consumer 的 lease，写业务、唯一 `(event_id,consumer)` receipt，commit 后 ACK。重复发布只重放未成功消费者；通知 `(user_id,event_id)` 唯一，分录使用 business_key 永久唯一，不能只靠短 TTL 缓存去重。

relay 标记 published 表示事件交给持久总线或 outbox 的全部同步消费者已成功，不代表远端邮件真正送达。邮件/短信 delivery 独立状态/重试/死信。处理失败有限指数退避+抖动，达到最大次数标 dead 并报警；不吞异常后继续确认。

Redis Streams/rabbit/kafka 至少一次；consumer group pending reclaim、lease/fence 防旧消费者 commit。Outbox 模式也使用 DB 领取租约。配置失效需广播所有 API 实例，不以单一 consumer group 把失效只投给一个实例；使用版本读取/L1 短 TTL兜底。

跨聚合事件可能乱序：消费者依据主库当前聚合状态和 version，不将旧 paid 事件覆盖新的 refunded 状态。索引按 version 更新，奖励发放经订单 service 再验证。事件 payload 不是授权事实来源。

关闭插件不消费对应事件，保留以便重启恢复；独立 outbox 发布状态不能让未来启用的消费者丢掉待处理事件，需按消费者游标/receipt 回读。站内信 5 秒目标依赖 poll≤2秒及未积压，不代表 M0 已验证延迟。
