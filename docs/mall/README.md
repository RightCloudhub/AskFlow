# AskFlow 商城

工作分支 `feat/mall-platform`。2026-10-29 用户确认继续，采用 M0 推荐默认值。此次仅编写代码、迁移、测试和部署材料，不运行服务或任何验证。

| 文档 | 内容 |
|---|---|
| [阅读笔记](./00-reading-notes.md) | 基线、工程指标、兼容边界和提示冲突 |
| [ADR 003](../adr/003-mall-modular-monolith.md) | 插件/模块边界、身份与客服复用 |
| [ADR 004](../adr/004-infra-ports-and-lite-mode.md) | 可关闭基础设施、配置与降级 |
| [ADR 005](../adr/005-wallet-double-entry.md) | 复式账、并发、退款和对账 |
| [数据模型](./data-model.md) | ER、表、唯一键与事务不变量 |
| [API](./api.md) | 路由、鉴权、错误、写入/分页契约 |
| [OpenAPI 草案](./openapi.yaml) | 核心请求与响应结构；运行时生成文档为最终契约 |
| [状态机](./state-machines.md) | 订单/支付/退款/预占/奖励/会话 |
| [事件](./events.md) | 信封、生产者/消费者、去重与租约 |
| [基础设施矩阵](./infra-matrix.md) | 两档实现、多实例安全与差异 |
| [决策与风险](./decisions.md) | 推荐默认值与真实上线待确认项 |
| [验证说明](./validation.md) | 后续需运行的测试/构建/迁移/压测命令 |
| [性能](./performance.md) | 目标、基准、报告模板；无实测数字 |
| [安全清单](./security-checklist.md) | ASVS L2/API Top 10 与验证要求 |
| [运维](./runbook.md) | 两档部署与资金/回调/队列故障处理 |

默认 full 等五个客服 profile 不包含商城。使用 mall、mall-lite 或 mall-only；基础设施独立通过 ASKFLOW_INFRA 切换。

支付/退款对 mock 网关可实际执行，但这不是支付宝/微信/Stripe 生产连接器。物流是 mock。console 邮件/短信不真实外发。部署、并发、安全、覆盖率和性能只有运行验证后才能验收。
