# ADR 004：基础设施端口与轻量模式

日期：2026-10-29。状态：Accepted defaults（用户 `keep going`）。相关：[基础设施矩阵](../mall/infra-matrix.md)。

## 决策

端口与适配器位于 `app/commerce/infra/`，复用现有数据库、outbox 和限流实现；不把基础设施后端变成 feature。Settings 保持唯一配置入口，采用分组 mixin/子模块拆分，避免向 config.py 堆积到超出 300 行。所有重型客户端延迟导入，lite 安装无需 Redis/ES/S3/MQ SDK。

ASKFLOW_INFRA=lite|full|custom 只决定未显式指定字段的默认值。逐项覆盖优先，读取 `model_fields_set` 或等价输入来源判断，不能用“值等于默认”判断用户是否显式设置。DATABASE_URL 始终权威，不偷偷切库。默认 custom 保持既有 SQLite/进程内行为；mall-lite compose 显式设置 lite。

full 未配置必要连接串/客户端时 fail-fast，不能悄悄采用 memory 并报告 redis。可选依赖中断时，只对可以安全降级的读端口自动回落；生产协调端口故障时写请求 503/429，禁止多实例自动改成进程锁。

## 配置

| 字段/环境变量 | 范围与默认 |
|---|---|
| ASKFLOW_INFRA | custom 默认；full 或 lite 显式选择 |
| DATABASE_URL / DATABASE_READ_URLS | 主库沿旧默认；副本逗号或 JSON 列表，默认空 |
| DB_POOL_SIZE / DB_MAX_OVERFLOW / DB_POOL_TIMEOUT / DB_POOL_RECYCLE | PG 池配置；不传给 SQLite/StaticPool |
| SQLITE_BUSY_TIMEOUT_MS / SQLITE_WAL | busy_timeout 命名配置、文件库 WAL；内存测试不假装 WAL |
| CACHE_BACKEND | memory 默认；redis/memory/off；off 只禁缓存，不禁 DB |
| LOCK_BACKEND | memory 默认；redis/pg/memory |
| RATE_LIMIT_BACKEND / RATE_LIMIT_ENABLED | memory 默认或 redis；关闭开关需在生产多实例策略中明确评估 |
| EVENT_BUS | outbox 默认；redis_streams/rabbitmq/kafka/outbox |
| FLASH_SALE_BACKEND | database 默认；redis，单独于缓存和锁 |
| SEARCH_BACKEND | like 默认；elasticsearch/pg_fts/sqlite_fts/like |
| OBJECT_STORE / LOCAL_OBJECT_DIR | local 默认或 s3；本地路径部署控制 |
| NOTIFY_EMAIL / NOTIFY_SMS | console 默认；smtp 或注册的短信 provider |
| SESSION_BACKEND | database 默认或 redis；数据库仍持久保存 refresh family |
| WORKER_MODE / MALL_WORKER_ENABLED | inprocess 默认或 separate；test 不自动运行 |
| INSTANCE_COUNT / WEB_CONCURRENCY | 默认 1；K8s 副本由清单显式注入 INSTANCE_COUNT |
| 外部调用 TIMEOUT/RETRY/BREAKER 字段 | 命名 Settings，有上限；金额与时间预算分离 |

full 预设：PG 主库/可选副本、redis cache/lock/limit/session/flash、redis_streams、elasticsearch、s3、separate worker；邮件短信仍 console，真实外发显式配置。lite 预设：SQLite、memory/off 缓存、memory 锁/限流、database 秒杀、outbox、sqlite_fts（不可用时 LIKE）、local、DB 会话、console、inprocess。

## 数据库与事务

SQLite 文件库启用 foreign_keys、WAL、busy_timeout，写事务由专用 transaction helper 在任何读之前 BEGIN IMMEDIATE；未使用该 helper 的原客服路径保持原 get_db 行为。不能在已有事务中再次 BEGIN。单容器一 API worker，DB 条件更新和唯一键兜底；数据库忙有限退避，不能吞异常假成功。

PG 使用 asyncpg 池，库存 UPDATE available>=qty；wallet 快照 CAS+非负余额；订单状态 CAS。Redis 锁是性能协调，不是资金正确性的唯一依据。读后写升级事务、权限检查、结算价格、库存、支付/退款确认、财务与写后读都使用主库。

只读仓储显式选择 read session，副本随机/轮询；同请求写后 sticky primary，客户端可带服务端签名的短期主库粘滞凭据。GET 不代表必然可走副本。副本失联可回主库，但不改变用户归属校验。

## 缓存、锁、限流

缓存 Cache-Aside：参数校验、短期空值、随机 TTL、进程 L1+Redis L2；同 key 单飞回源。写后只在 commit 后失效 L1，同时 outbox 广播失效 L2/其他实例。缓存中的上架/价格/余额不能作为写入判定依据。

Redis 锁使用 SET NX PX 与 owner token，Lua 续期/释放，INCR 单调 fencing token；数据库更新记录 fencing 或 CAS 版本阻挡过期持有者。PG advisory lock 使用稳定哈希和同一连接生命周期；内存分片 Lock 防无限 key 增长。

限流全局/IP/用户/接口 + 秒杀独立令牌桶。用户来自已验证 JWT，不直接相信请求头；代理 IP 复用 trusted_proxy_hops。Redis Lua 原子计数/滑动窗口；memory 复用当前 middleware。429 包含 Retry-After；关掉可选层后生产仍保留认证/资金风控硬限制。

## 事件与 worker

数据库 outbox 为权威，无论选择什么总线都先写 outbox。完整信封见 events.md，复用 emit/relay；扩展 AppContext 的消费者槽，未知商城事件不能提前被旧 relay 标记 published。

多副本 relay 使用 DB 租约/条件领取；每消费者 event_id 唯一回执与业务变更同事务。Redis Streams consumer group 需 pending reclaim，ACK 只能在 DB commit 后；发布重复允许、业务重复禁止。RabbitMQ/Kafka 为可选适配器，只有实现通过合约测试才允许配置。

秒杀 full Redis Lua 预扣/用户限购/请求 token → Stream → worker 落单，仍经 DB 库存条件更新；失败恢复 Redis 配额，超时预扣通过任务/对账修复。lite 同步 DB 路径，更严格入口限流。不能宣传“预扣成功=订单成交”。

过期预占、查单补偿、奖励成熟、通知重试、幂等清理、对账均使用 DB 租约。lease_owner/fencing/version 防旧 worker 提交；无网络操作长期持有事务；separate 模式 API 不重复启动商城循环。

## 安全护栏与健康

assert_startup_safe 在商城启用时校验支付 HMAC、TOTP 加密、refresh 哈希密钥的强度和独立性；不影响未启用商城的旧 profile。生产多实例遇 memory 协调/限流、SQLite 或 inprocess-only 秒杀队列拒绝启动；development 输出降级告警。

K8s 清单显式注入期望副本数，HPA min/max 与 INSTANCE_COUNT 一致；无法自动发现未来副本数时不能声称安全检测完整。lite overlay replicas=1，禁止 HPA。

GET /api/v1/admin/infra 只读、需权限；输出实现/多实例安全/降级/健康，不输出 URL、账号、密钥。/health/live 仅进程状态；/health/ready 检查关键 DB/协调依赖、schema；缓存/搜索/外发降级不踢掉所有实例。沿旧 /health 响应兼容扩展。

## 备选与后果

把 infra 放 core 会扩大旧客服导入面，因此端口先放 commerce，必要的 DB/认证公共增强留 core。强制所有环境 Redis/PG 会破坏离线测试与轻量部署，因此不选。

轻量模式降低读写吞吐、复制与容灾能力，不等于可承载生产多实例。完整实现使用相同业务 service，差异由端口合约测试、双档集成和压测取证；M0 未运行任何验证。
