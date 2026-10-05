# 完整设置参考

[配置指南](README.md)

本参考涵盖当前应用和服务任务设置类中的每个字段，以及前端功能覆盖。如果你不确定是否需要某个设置，请先阅读演练章节。

除非另有说明，请在 **API** 环境或 `apps/api/.env` 中设置这些项，并**重启 API**。没有显式别名的名称使用此处所示的大写字段名。默认值是源码默认值，不一定等于你的安装提供的可能不同的值。

**未设置（Unset）** 表示省略该设置。**空文本（Empty text）** 表示空字符串。布尔值使用 `true`/`false`，计数/时长使用十进制数字，指定的结构化字段使用 JSON，命名选项使用精确拼写。大多数字段没有严格的范围验证；除非文档记录了明确的关闭值，否则请保留有意义的正值。

## 运行时与访问

请参见 [基础](basics.md) 和 [账号、访问与托管](access.md)。

| 名称 | 默认值 | 含义和限制 |
| --- | --- | --- |
| `APP_NAME` | `AskFlow` | API 标题/根名称；不会重塑 Web 界面的品牌 |
| `APP_VERSION` | `0.1.0` | 用于进程报告的版本标签；不会升级软件或覆盖每个包版本显示 |
| `ASKFLOW_ENV` | `development` | `development`、`test`、`staging` 或 `production`；test 禁用后台循环 |
| `DEBUG` | `false` | 已声明，但当前未接入应用调试行为 |
| `API_PREFIX` | `/api/v1` | API 路由前缀；更改它需要前端/代理协调更改 |
| `CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | 浏览器来源的 JSON 数组；不是裸的逗号分隔文本 |
| `SECRET_KEY` | `change-me-in-production` | 登录签名密钥和回退 webhook 密钥；请替换为生成的私有值 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | 普通登录令牌生命周期（分钟）；微件令牌有单独的固定生命周期 |
| `JWT_ALGORITHM` | `HS256` | 令牌签名算法；除非更改认证集成，否则请保留 |
| `RATE_LIMIT_PER_MINUTE` | `60` | 每进程每分钟每 IP 的 HTTP 请求数；有效最小值 1；不是分布式或 WebSocket 消息限制 |
| `TRUST_PROXY_HEADERS` | `false` | 为限流信任转发的客户端 IP；仅在受控代理后面启用 |
| `DISABLE_LOCAL_REGISTER` | `false` | 为 true 时在所有模式下阻止本地自助注册 |
| `ALLOW_LOCAL_REGISTER` | `false` | 除非明确禁用，否则允许 staging/production 中的本地注册 |
| `ALLOW_BOOTSTRAP_ADMIN` | `false` | 允许 staging/production 中的第一个用户管理员引导；development/test 单独允许 |
| `METRICS_TOKEN` | 未设置 | 在 staging/production 中设置时，仅对 `/metrics` 要求 `X-Metrics-Token` 值 |
| `ASKFLOW_PROFILE` | `full` | 功能包：`core-only`、`faq-only`、`mvp`、`enterprise`、`full` |
| `ASKFLOW_FEATURES` | 空文本 | 逗号分隔的添加/移除，例如 `+teams,-mcp`；依赖项可能把移除的前置功能加回来 |

## 存储与文档处理

请参见 [存储与索引](storage.md)。文件位置取决于 API 工作目录。

| 名称 | 默认值 | 含义和限制 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./askflow.dev.db` | 数据库地址；PostgreSQL 使用 `postgresql+asyncpg://...`；更改它不会迁移记录 |
| `REDIS_URL` | 未设置 | 用于可选索引队列和共享取消的 Redis 连接；已保存的服务任务不需要 |
| `S3_ENDPOINT` | 未设置 | 保留；标准上传仍保留在本地 |
| `S3_ACCESS_KEY` | 未设置 | 保留的 S3 凭据；本地上传适配器不使用 |
| `S3_SECRET_KEY` | 未设置 | 保留的 S3 机密；本地上传适配器不使用 |
| `S3_BUCKET` | `askflow` | 保留的存储桶名称；不会切换存储 |
| `CHROMA_PERSIST_DIR` | 未设置 | 可选的本地 Chroma 目录；需要向量依赖 |
| `CHROMA_HOST` | 未设置 | 可选的 Chroma 主机，不带方案/路径；优先于本地目录 |
| `CHROMA_PORT` | `8001` | Chroma 服务器端口；捆绑容器的内部端口是 8000 |
| `CHROMA_COLLECTION` | `askflow` | Chroma 集合名称；保持集合内的向量兼容 |
| `INDEX_ASYNC` | `false` | 在测试模式之外将上传/重建索引排队，而不是在请求中完成 |
| `INDEX_WORKER_ENABLED` | `true` | 在测试模式之外启动 API 内的索引消费者 |
| `INDEX_WORKER_POLL_SECONDS` | `1.0` | 空闲轮询延迟（秒）；有效至少 0.2 秒 |
| `INDEX_QUEUE_KEY` | `askflow:index_jobs` | Redis 列表名称；区分共享 Redis 的独立安装 |
| `REVISION_STORE_DIR` | `./data/revisions` | 文档修订快照；更改它不会移动旧快照 |
| `MAX_UPLOAD_BYTES` | `15728640` | 最大上传字节数：15 MiB；代理限制可能更小 |
| `CANCEL_TTL_SECONDS` | `300` | 共享取消支持中取消标记的生命周期；不是服务任务期限 |

此类中没有配置上传目录字段：标准适配器使用 `./data/uploads`。没有全局备份调度、归档保留或自动完整索引恢复变量。

## 模型、搜索和对话上下文

关于所需的 URL 形式和嵌入更改，请参见 [模型与答案质量](models.md)。

| 名称 | 默认值 | 含义和限制 |
| --- | --- | --- |
| `LLM_BASE_URL` | 未设置 | 对话服务基础地址，**不带 `/v1`**；也是嵌入的回退基础地址 |
| `LLM_API_KEY` | 未设置 | 对话凭据；也是嵌入的回退凭据 |
| `LLM_MODEL_GENERATE` | `gpt-4o-mini` | 知识答案模型 ID |
| `LLM_MODEL_CLASSIFY` | `gpt-4o-mini` | 路由器中的分类选择/回退候选；不会替换默认的规则分类器 |
| `LLM_MODEL_REWRITE` | `gpt-4o-mini` | 路由器中的改写选择；默认查询改写仍基于规则 |
| `LLM_MODEL_SUMMARY` | `gpt-4o-mini` | 使用时的摘要/草稿辅助选择和回退候选 |
| `LLM_TIMEOUT_SECONDS` | `60.0` | 模型 HTTP 超时，也用于已配置的嵌入；流式对话读取超时单独固定为 120 秒 |
| `EMBEDDING_BASE_URL` | 未设置 | 嵌入基础地址，**不带 `/v1`**；回退到对话基础地址 |
| `EMBEDDING_API_KEY` | 未设置 | 嵌入凭据；回退到对话凭据 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 远程嵌入模型 ID；无远程连接意味着离线哈希嵌入 |
| `EMBEDDING_DIM` | `384` | 离线向量维度和配置的远程维度元数据；不请求提供商端调整大小 |
| `REWRITE_SYNONYM_PATH` | `../../data/samples/query_synonyms.yaml` | 同义词 YAML 路径；使用受控的真正等价词文件 |
| `GROUNDING_THRESHOLD` | `0.35` | 最高可用证据分数的最低值；降低会接受更弱的证据 |
| `GROUNDING_MIN_HITS` | `1` | 可用搜索命中的最小数量 |
| `GROUNDING_WEAK_SOURCES` | `2` | 在证据不足响应中包含的弱来源段落数量 |
| `MAX_QUESTION_CHARS` | `2000` | 请求防护中的问题最大字符数 |
| `MAX_ANSWER_CHARS` | `4000` | 输出字符界限；当前生成器也会将此数字作为模型 `max_tokens` 传入 |
| `MAX_HISTORY_MESSAGES` | `20` | 先前消息上下文界限；不是数据库保留 |
| `MAX_HISTORY_CHARS` | `6000` | 先前文本上下文界限；不是数据库保留 |
| `RETRIEVAL_CACHE_TTL_S` | `60` | 搜索缓存生命周期（秒）；`0` 禁用它 |
| `RETRIEVAL_CACHE_MAX_ENTRIES` | `256` | 每进程缓存容量；有效最小值 1 |
| `HISTORY_SUMMARY_THRESHOLD` | `12` | 当其长度超过此计数时压缩历史 |
| `HISTORY_SUMMARY_KEEP_RECENT` | `4` | 与压缩历史一起保留的最近消息；有效最小值 1 |

这些模型名称记录的是代码默认值。它们不承诺你的提供商提供这些模型，也不是当前价格/性能建议。

## 请求处理、任务和客服服务

请参见 [服务运营](service.md)。第一组限制适用于较旧的消息/工具循环，而不是所有已保存任务的执行。

| 名称 | 默认值 | 含义和限制 |
| --- | --- | --- |
| `MAX_LOOP_STEPS` | `6` | 较旧工具循环的步骤预算 |
| `MAX_TOOL_CALLS` | `4` | 较旧工具循环的调用预算 |
| `MAX_WALL_MS` | `45000` | 较旧循环的墙钟时间预算（毫秒）：45 秒 |
| `MAX_RETRIES_PER_TOOL` | `2` | 较旧循环的重试界限；重试行为还取决于失败类型 |
| `MAX_SLOT_TURNS` | `3` | 收集缺失工具参数（例如订单号）时的后续询问界限 |
| `INTENT_CLARIFY_THRESHOLD` | `0.45` | 请求澄清的路由防护置信度阈值 |
| `HARNESS_POLICY_VERSION` | `1.0.0` | 记录的防护策略版本标签；更改它不会安装不同的策略代码 |
| `SERVICE_TASKS_ENABLED` | `true` | 已保存任务接收/worker，还需要 agent 功能；测试模式抑制后台 worker |
| `SERVICE_TASKS_GOALS` | `order_status` | 逗号分隔的接收允许列表；可用的附加策略是 `ticket_resolution,human_handoff`；为空则停止新的已保存目标接收 |
| `SERVICE_TASK_POLL_SECONDS` | `5.0` | 已保存任务 worker 扫描间隔；验证最小值为 1 秒 |
| `ORDER_LOOKUP_URL` | 未设置 | 完整的订单 HTTP 端点；已保存任务路径发送订单/客户 ID |
| `ORDER_LOOKUP_TOKEN` | 未设置 | 订单端点的可选 bearer 令牌 |
| `HANDOFF_TIMEOUT_SECONDS` | `300` | 无人认领的转人工请求超时的时长阈值 |
| `SWEEPER_ENABLED` | `true` | 测试模式之外的定期转人工/SLA 检查 |
| `SWEEPER_INTERVAL_SECONDS` | `60` | 定期转人工/SLA 扫描间隔；有效至少 15 秒 |

已保存任务预算、对象锁定时长、订单 HTTP 超时、SLA 策略和偏好保留有单独的代码或请求级控制。不要从上面的字段推断它们的环境变量名。

## 外部集成和可选扩展

请参见 [账号](access.md)、[服务运营](service.md) 和 [渠道](channels.md)。配置凭据不一定启用相应功能或完成其集成。

| 名称 | 默认值 | 含义和限制 |
| --- | --- | --- |
| `NOTIFY_WEBHOOK_URL` | 未设置 | 事件接收方 URL；未设置意味着本地接收器而非外部通知 |
| `NOTIFY_WEBHOOK_SECRET` | 未设置 | Webhook 签名密钥；回退到 `SECRET_KEY` |
| `OIDC_ISSUER` | 未设置 | 用于 ID 令牌验证的确切身份提供商服务方 |
| `OIDC_CLIENT_ID` | 未设置 | 预期的 ID 令牌受众/客户端标识符 |
| `OIDC_MOCK` | `false` | 开发用 mock 身份模式；在 staging/production 中被禁止 |
| `MCP_ENABLED` | `false` | 已实现的已批准工具注册的门控，不是远程 MCP 连接 |
| `MCP_TOOL_WHITELIST` | `search_knowledge` | 逗号分隔的允许名称；未知工具可能是 echo 桩 |
| `SIEM_WEBHOOK_URL` | 未设置 | 明确的审计推送目的地；不会启动自动转发 |
| `FEISHU_VERIFICATION_TOKEN` | 未设置 | 飞书事件验证值；预期的经过认证的生产设置需要 |
| `FEISHU_APP_ID` | 未设置 | 飞书出站回复应用 ID |
| `FEISHU_APP_SECRET` | 未设置 | 飞书出站回复应用凭据 |
| `WECOM_TOKEN` | 未设置 | 受支持的普通/测试验证令牌；不是完整的生产 POST 认证 |
| `WECOM_CORP_ID` | 未设置 | 保留的企业标识符；无活跃的出站使用 |
| `WECOM_AGENT_ID` | 未设置 | 保留的应用标识符；无活跃的出站使用 |
| `DINGTALK_APP_SECRET` | 未设置 | 适配器支持的消息签名格式的密钥 |
| `DINGTALK_APP_KEY` | 未设置 | 保留的应用密钥；无活跃的出站使用 |
| `BOT_PROFILES_JSON` | 空文本 | 作为字符串存储的 profile 对象 JSON 列表；格式错误的内容会被加载器忽略 |
| `DEFAULT_BOT_ID` | `default` | 默认机器人 profile 查找 ID；不是单独的租户/安全边界 |
| `DEFAULT_LOCALE` | `zh-CN` | 有限后端本地化的默认值；目录还包含 `en-US`；不会翻译 Web UI |
| `REASONING_ENABLED` | `false` | 为匹配较旧循环意图启用可选的额外步骤 |
| `REASONING_INTENT_WHITELIST` | `product_faq,troubleshoot` | 确切的逗号分隔意图名称；默认值不匹配正常的内置意图词汇表 |
| `REASONING_MAX_STEPS` | `2` | 额外的匹配循环步骤；负值实际上不添加任何步骤 |
| `SANDBOX_ENABLED` | `false` | 仅工具门控；不提供沙箱隔离或安装执行服务 |

## 仅前端设置

| 名称 | 默认值 | 位置和效果 |
| --- | --- | --- |
| `VITE_ASKFLOW_FEATURES` | 未设置 | `apps/web/.env.local` 或 Web 构建环境；完整的逗号分隔功能列表，不带 `+`/`-`；重启 Web 开发服务器或重新构建/重新部署 |

自动发现失败时回退到仅核心，且当前需要客服/管理员访问权限。关于将前端列表与后端匹配并支持客户导航，请参见 [功能](features.md)。绝不要把凭据放入前端环境值。

## 在其他地方编辑的设置

| 配置 | 在哪里更改 |
| --- | --- |
| 意图到路由的覆盖 | **Admin → 意图路由**；保存在数据库中 |
| 提示词内容/活动版本 | **Admin → 提示词模板**；消费因响应路径而异 |
| 团队和客服成员资格 | 创建/添加使用 **Admin → 技能组**；其他更改需要集成 |
| 账号启用/禁用状态 | **Admin → 用户管理** |
| 账号角色 | 运维人员开通或经过验证的 SSO 角色映射；网页中没有角色编辑器 |
| 连接器 URL、方法、头、超时 | 经授权的连接器 API；单独的数据库记录 |
| 知识内容 | **Admin → 知识文档 / 知识草稿** |
| 按客户保存的偏好 | 经过认证的偏好 API；没有标准偏好页面 |
| 监听端口、HTTPS、反向代理、备份 | 服务器/托管配置，位于应用设置类之外 |
| SLA 目标时长和完整任务预算 | 代码/集成控制；此版本中不是浏览器/环境变量调优 |

对于拼错、不受支持或无效的设置，请使用 [验证与故障排查](troubleshooting.md)。
