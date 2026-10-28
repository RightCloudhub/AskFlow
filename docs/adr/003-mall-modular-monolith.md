# ADR 003：商城采用同仓模块化单体

日期：2026-10-29。状态：Accepted defaults（用户 `keep going`）；上线业务参数仍见决策清单。相关：[阅读笔记](../mall/00-reading-notes.md)。

## 决策

在 `apps/api/app/commerce/<module>/` 新增领域，作为 `app/plugins/builtin/mall_*.py` 插件装配。共用 FastAPI、Settings、数据库事务、users、审计、outbox 和 Action Gateway。每个模块拥有自己的表，外部模块只使用 service 接口、不可变 DTO 和事件，禁止导入别人的 repository/models 做查询。

模块内使用 models/schemas/repository/service/api/events，按职责继续拆分；不是为了凑目录创建空业务文件。新增与改动代码满足六项硬指标。共享基础类型和事务工具放 `commerce/core/`；可关闭的基础设施放 `commerce/infra/`，详见 ADR 004。

## 插件图

| 插件 | 强依赖 | 职责 |
|---|---|---|
| mall_core | core | 金额/错误/幂等/事件/端口装配、公开商城发现、基础设施视图 |
| mall_account | mall_core | users 扩展、认证增强、step-up、资料和地址 |
| mall_catalog | mall_core | 类目、SPU/SKU、价格、上架和搜索 |
| mall_inventory | mall_catalog | 库存、预占、流水、秒杀 |
| mall_order | mall_inventory,mall_account | 购物车、结算、订单、退款申请和状态 |
| mall_payment | mall_order | 支付和退款网关编排、mock、查单补偿 |
| mall_wallet | mall_account | 记账、余额、充值、冻结和对账 |
| mall_referral | mall_wallet | 单层邀请、防刷、奖励和冲正 |
| mall_notify | mall_core,notify | 站内信、模板、偏好和投递 |
| mall_support | mall_order,ticket,handoff | 客服上下文/关联、工单通知；条件装配 Agent 桥 |
| mall_admin | mall_core | 权限、配置、审批、运营/财务视图；各域 API 由所属插件挂载 |

payment/wallet 之间不增加循环 depends：由 core 注册支付和记账 service 端口，payment 在 wallet 启用时提供钱包/组合支付，否则仅第三方；wallet 在 payment 缺失时禁止充值，但保留余额/流水。引用未装配端口返回明确的 capability_unavailable，不能假成功。

mall_order 可独立追加，不因退款申请功能隐式启动支付/钱包。售后受理可挂起；执行退款要求 mall_payment 已启用。mall_admin 的菜单/API 按实际域启用状态注册，关闭目录不能通过后台绕过。

## Profile

| 新 profile | 清单 |
|---|---|
| mall | 现有 mvp 的全部插件 + 全部 mall_*；依赖闭包补 notify |
| mall-lite | core,rag,agent,tools,ticket,handoff,notify,widget + 全部 mall_*；配套 ASKFLOW_INFRA=lite |
| mall-only | core,ticket,handoff,notify + 全部 mall_*；不装配 rag/agent/tools/widget |

mall_support 的 Agent 依赖调整是为了让 mall-only 真正无 AI。只有 `ctx.enabled("agent")` 才注册 mall.* 聊天能力及持久策略。工单/人工与 Gateway 可独立使用，无 LLM 不影响商城。

旧 full/enterprise/mvp/faq-only/core-only 的清单、默认 full、测试语义保持不变；商城只能通过新 profile 或显式 feature 增量启用。不支持第三方动态热安装。关闭插件仍保留表与财务记录。

## 身份与认证兼容

商城客户使用现有 users，role=user；不复制用户、不改变现有邮箱/role/oidc_subject 语义。user_profiles/security/sessions 等扩展表负责商城信息。商城公共注册始终创建 user，不走原首账号 admin bootstrap。

所有密码/短信/旧认证/商城认证/OIDC/WS 入口共用安全校验：启用 MFA 后旧登录不能签发绕过 MFA 的可用商城会话；注销、禁用、refresh family 吊销和 access jti 吊销对客服访问同样生效。旧 profile 中无扩展安全记录的用户保持原行为。

MALL_PUBLIC_REGISTER 是 production/staging 显式 opt-in，DISABLE_LOCAL_REGISTER 为最高优先级 deny；不借商城注册绕过部署的强制 SSO 政策。OIDC 客户可下单；若启用本地 MFA，OIDC 登录后需 step-up 建立商城敏感操作凭证。

## 订单、退款与客服边界

`scoped_order` 在 mall_order 启用且 ORDER_LOOKUP_URL 为空时调用进程内 OrderService.lookup(owner_id,order_id)，返回与旧扁平契约一致的具体数据库状态。配置了 URL 时保持 HTTP 优先。跨客户和不存在均 404，不向模型暴露他人订单。

额外挂载 root-level `GET /internal/mall/orders/lookup`，仅服务 bearer ORDER_LOOKUP_TOKEN、非空密钥、常量时间比较；customer_id 是可信服务调用参数。不能使用客户 JWT 调用，也不作为公开商城 API。

mall.refund.submit 和兼容 refund.submit 使用现有 Gateway：irreversible_write、L2、参数绑定的单次确认、超限运营审批。额度来自整数分商城政策；兼容旧非商城欧元策略。取消仅直接取消未支付订单；已支付未发货需要确认退款流程，不能释放库存后遗留资金。

同步业务事务依次调用各域 service，库存/订单/钱包/事件整体提交或回滚。外部支付/退款分两步：先提交意图和业务支付/退款单，再调用网关；未知结果保留待查询状态，不在持有 DB 事务时无限等待网络。

工单用既有唯一仓储和 Gateway，人工用既有 HandoffService；support_links 扩展关联，不修改原 ticket 列语义。会话创建时附经授权查询得到的订单/钱包快照，客户传来的金额不作为事实。人工备注、卡号、验证码不进对话上下文。

## 备选方案

独立商城服务 + ORDER_LOOKUP_URL/webhook 可独立发布，隔离热点故障，但需要重建身份、审计、事务/幂等和服务认证，订单/客服失去本地事务边界。当前同语言栈、同部署单元，成本大于收益，因此不选。

未来独立团队/语言栈/发布节奏出现时，可沿 service 端口和事件拆分，内部 lookup 契约已预留。水平扩展先采用同镜像多 API/独立 worker，数据库和 Redis 负责协调。

## 验证要求与后果

增加跨域 service 合约、旧/新 profile 路由矩阵、认证防绕过、lookup 归属、Gateway 确认/审批和 outbox 去重测试。DB 仍为单一事务资源，热点与故障隔离不等同于微服务。部署/性能均待验证，不能仅因模块化宣称高并发达标。
