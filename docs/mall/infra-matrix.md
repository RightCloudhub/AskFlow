# 基础设施能力矩阵

状态：M0 设计；当前没有商城端口实现或实测。API /api/v1/admin/infra 与启动日志将输出本表的实际装配值/健康状态，不回显连接串。

| 端口 | full | lite/关闭 | 多实例安全与差异 |
|---|---|---|---|
| DB/事务 | PostgreSQL+asyncpg 池、可选只读副本 | SQLite 文件库 WAL+busy_timeout+BEGIN IMMEDIATE | PG 条件更新/行锁；SQLite 单写者，单 API worker，无故障切换 |
| cache | Redis L2 +进程 L1 | memory TTL LRU 或 off | memory 每实例独立；资金判定不依赖缓存；off 完全回 DB |
| lock | Redis owner/fencing/续期或 PG advisory | 分片 asyncio.Lock | 内存仅本进程；数据库条件更新仍兜底；生产多实例禁 memory |
| rate limit | Redis Lua 滑动窗口/令牌桶 | 现有 memory middleware | memory 每实例计数；四层限流/秒杀独立；429 Retry-After |
| event bus | Redis Streams；可选 RabbitMQ/Kafka | DB outbox +轮询 relay | outbox 总是权威；所有档 consumer receipt/lease；lite 延迟/吞吐较低 |
| flash ingress | Redis Lua 预扣+请求 token+Stream | 同步 DB 预占 | full 入队不等于成交；DB 不超卖兜底；lite 更严格限流 |
| search | Elasticsearch/OpenSearch | PG FTS/SQLite FTS5/LIKE | ES 故障回 DB；FTS5 不可用明确 LIKE；无同等相关性/聚合 |
| objects | S3/MinIO | 本地部署目录 | 本地无 CDN/共享盘；路径由服务生成，类型/大小校验 |
| sessions/revocation | Redis缓存+DB持久家族 | DB+短 TTL memory | DB 为 refresh/replay 权威；严格吊销查 DB，不能因缓存 stale 接受已撤销token |
| email/SMS | SMTP/注册provider，默认console | console +站内信 | console 无真实外发；不记录凭据正文；失败不阻断必有站内信 |
| scheduled work | 独立 worker 多副本 DB 租约 | API inprocess | 同一业务任务的 fence/CAS 仍存在；test 不自动启动 |
| external resilience | timeout/retry/breaker | 同协议包裹mock | 只读可重试；未知资金写先查证；搜索可降级、资金拒绝假成功 |
| tracing | 可选 OpenTelemetry | trace_id+结构化日志 | 默认关；无 SDK 仍可导入；业务 ID 只放日志/trace，不作 metrics label |

full/lite 是未覆盖配置的默认值。显式 Redis/memory 覆盖在能力矩阵如实显示。基础设施 disable 不改变插件列表；关掉 mall_order 路由404，不是“memory订单”。

生产多实例关键协调不可在故障时自动切 memory；Redis 失联可关缓存/降级搜索，但库存/支付入口按照可用数据库协调策略明确503，或通过显式配置选择 PG 锁与DB秒杀后重新部署。
