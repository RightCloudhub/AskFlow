# 商城部署与运维

状态：设计/待运行材料。本轮没有启动或部署；配置文件存在不代表从零全流程验收成功。运行清单见validation.md。

## 两档部署

lite：一个API容器、SQLite持久卷、本地对象目录、memory协调/outbox/inprocess、console外发；一API进程/replica，无Redis/PG/ES。开发demo可用mock验证码收件箱，production不能公开凭据。配置ASKFLOW_PROFILE=mall-lite，ASKFLOW_INFRA=lite。

full：PG主库+只读副本、Redis、MinIO、ES、多API、独立worker、nginx；先一次migration job，再API/worker。PG复制用于读扩展，自动主库选举/故障切换未交付。对象bucket/ES索引初始化独立job，凭据环境注入，不写入版本库。

知识修订文件由 API 与索引 worker 共享：Compose 使用 revisions 数据卷，Kubernetes full 使用支持 ReadWriteMany 的 mall-revisions PVC；lite 保存在单一数据卷。配置正确的存储类并将修订文件纳入备份，不能让多副本使用互不共享的容器目录。

生产设置ASKFLOW_ENV、SECRET_KEY、METRICS_TOKEN、PAYMENT_CALLBACK_SECRET、MALL_TOTP_KEY、MALL_REFRESH_SECRET等独立强密钥；MALL_PUBLIC_REGISTER显式开才允许公共注册。INSTANCE_COUNT/WEB_CONCURRENCY必须与副本声明匹配；lite禁止多副本。

Web由同镜像或nginx静态资源服务，/api,/internal按不同访问策略，internal仅可信服务网络；健康区分live/ready，metrics仅内网token。CORS白名单，HTTPS，cookieSecure。worker与API同版本schema，separate模式API不启动商城重复循环。

## 对账差异

收到hash/借贷/负库存差异立即暂停相关资金/秒杀能力，保留原数据和日志，导出run/diff/journal/providerref。先确认主副本和snapshot读一致，再核对原网关账单。不得DELETE差异或UPDATE posting；正确分录需要两人审批冲正，单纯快照漂移需完整链验证后批准重建。

财务确认处置后关联adjustment/reversal并审计，重新reconcile。不以“报警消失”当作资金修复；需余额、借贷、hash、网关四项无未解释差异。

## 支付回调故障

区分验签失败、金额/币种冲突、DB事务失败与网关未回调；记录报文摘要/交易号，不记录签名密钥或用户token。pending/unknown由主动查单，查询原request_key；禁止另建支付/退款键盲重试。late_payment不能把取消订单推进PAID，转原路退款/清算审核。

mock支持成功/失败/延迟/重复/丢失/金额不符；真实网关上线另做沙箱验签和账单对齐。回调重放只生成一笔journal，恢复后对账再放量。

## Redis故障与轻量降级

缓存/搜索允许回DB；协调/秒杀/会话严格吊销不可悄悄改memory多实例。暂停秒杀入口，确认PG条件更新/锁可承担负载，显式选择pg锁、DB秒杀、outbox并滚动重启。需要lite时缩为单实例+SQLite迁移/导出方案，不能直接把生产PG资金库URL改SQLite。

Streams积压需先恢复pending reclaim/DBreceipt，ACK在commit后；不要删除stream消除告警。Redis预扣与DB落单对账修复，未成交预扣最终释放。

## 秒杀与库存

预案先预热详情/活动，验证DB库存、Redis预扣、限购和请求token一致。入口限流优先429，queued不是成交。监控negative_inventory/oversell恒为0、queue lag、5xx、P99。出现差异停活动并保留请求/预占/订单映射，不手改available掩盖。

过期释放用lease/fence/CAS，支付vs取消共享订单锁。释放卡住检查worker模式/租约/DBbusy，不通过批量“全部释放reserved”处理。

## 配置、权限与回滚

仅白名单mall_settings可热改，version+修改人+审计；rollback创建新版本并outbox失效。支付密钥/数据库/基础设施/Harness不热改运营配置。赋权/2FA重置/调账审批分离。

应用回滚前核对schema兼容与未结支付/退款；数据库生产downgrade会丢数据，必须专项批准和备份。关闭mall插件保留表/账，不以卸载清空商城数据。

## 用户/管理员操作

客户/shop：注册验证→登录/MFA→浏览/购物车/quote→下单→mock支付→订单/退款；钱包充值/流水、邀请、消息、账号设置。联系支持携带order/refund/journal引用，经service校验后进入既有AskFlow会话/工单/人工。

后台/admin/mall：运营维护商品/库存/订单，财务查看wallet/reconcile并双人调账，客服仅授权订单快照，审计角色只读。所有写操作有before/after与actor；前端菜单权限隐藏不替代后端检查。
