# 后端加固与规划（2026-10-11）

范围：`apps/api`。基线：`main@49672f2`。本轮目标是把 2026-07-18 审计发现的缺陷与
`TODO/chat-response-latency.md` 中的性能瓶颈全部落地，并给出剩余的后端路线图。

写法约定：只在真正的信任边界（外部请求、IdP、Webhook）做校验；内部调用直接失败、直接抛错，
不再用 `try/except: pass` 吞异常或给内部数据层层兜底。

## 1. 已完成

### 1.1 安全

| 编号 | 问题 | 处理 |
|---|---|---|
| D-02 | OIDC 按 email 关联已有账号且不看 `email_verified`；组路径后缀 `/x/admin` 即授管理员 | 新增 `users.oidc_subject`（迁移 `20261011_user_oidc_subject`）：已绑定账号按 `sub` 识别；首次按 email 关联必须 `email_verified=true` 并写审计 `auth.sso_linked`；角色同步写审计 `auth.sso_role_changed`；角色映射改为整串匹配 |
| D-03 | 限流取 `X-Forwarded-For` 最左值，可伪造绕过 | 新增 `TRUSTED_PROXY_HOPS`，从右往左取第 N 个地址 |
| D-10 | 飞书 Webhook 只有静态 token，`==` 比较、无签名、无防重放 | 新模块 `channels/feishu/security.py`：`X-Lark-Signature` 校验、5 分钟时间窗、nonce 去重、加密事件解密、`hmac.compare_digest`；生产环境未配 `FEISHU_ENCRYPT_KEY` 拒绝所有事件 |
| D-16 | 限流按后缀跳过 `/health`、`/metrics`，任何同后缀路由都绕过 | 精确路径白名单 |
| D-17 | 限流字典从不清理空闲 IP | 每个时间窗清理一次空闲 key |
| D-18 | 生产未设 `METRICS_TOKEN` 时 `/metrics` 公开 | 生产/预发未设置则拒绝启动；常量时间比较 |

### 1.2 业务正确性

| 编号 | 问题 | 处理 |
|---|---|---|
| D-01 | `first_responded_at` 从未写入，所有工单误报首响 SLA 违约 | 工单离开 `pending` 或坐席在接管会话中首次回复时写入 |
| D-04 | 每轮 4 条预算种子被当作真实调用入库，成本页 `calls` 虚高 | 只持久化真实调用；`summary.calls` 只计真实调用 |
| D-05 | `ASKFLOW_FEATURES=-tools` 被依赖闭包悄悄加回 | 被依赖的插件不能单独移除，直接报 `ManifestError` 并指明依赖方 |
| D-06 | `faq-only`/`core-only` 没有 `refuse` 处理器，拒答降级为澄清 | `clarify`/`refuse` 移入 `core` 插件，所有 profile 都有 |
| D-09 | Webhook/指标在 `commit` 之前发出，回滚后重复通知 | 先提交状态变更，再发布；超时清扫与 SLA 扫描共用 `publish_*` |
| D-13 | 移除项拼写错误被静默忽略 | 移除项同样校验 |
| D-14 | “在吗”这类空泛消息走 RAG，澄清分支在离线模式下不可达 | 识别空泛寒暄并强制澄清 |
| D-15 | 订单号槽位多问一次 | 首次询问计入次数，`max_slot_turns=3` 恰好问 3 次 |

### 1.3 检索与知识库

| 编号 | 问题 | 处理 |
|---|---|---|
| D-07 | 融合去重只看文本前 64 字，同文档同前缀的不同分块被合并 | 以（文档, 完整文本）为键 |
| D-08 | GBK 文本被解码成乱码后照常入库 | UTF-8 / UTF-8 BOM / UTF-16 BOM / GB18030 严格解码，都不匹配则上传失败并提示 |
| D-11 | BM25 内存索引在事务提交前修改、重启后丢失 | 新增 `core/after_commit.py`：索引变更与文件删除在提交后执行、回滚即丢弃；`rag` 插件启动时从对象存储重建所有 ACTIVE 文档 |
| D-12 | 引用自检只认 `[n]` | 同时识别 `［n］`、`【n】` |
| D-19 | RRF 先截断 top-k，绝对分最高的命中可能被挤掉 | 绝对分最高的命中始终保留 |
| D-20 | 历史截断硬编码 2000 | `MAX_HISTORY_MSG_CHARS` 配置；超长提示文案随 `max_question_chars` 变化 |

### 1.4 响应速度（`TODO/chat-response-latency.md`）

| 级别 | 处理 |
|---|---|
| P0 流式被缓冲 | WS 直接推送 token；检索通过后立即推送引用；`commit` 之后再发 `intent`、副作用与 `message_end` |
| P0 首问冷启动 | `rag` 插件 `boot` 预热 BM25、种子向量与已上传文档 |
| P1 无连接复用 | LLM 与 embedding 客户端进程内复用 `httpx.AsyncClient`，关闭时 `aclose` |
| P1 检索串行 | BM25（线程）与向量检索并发；BM25 索引整体原子替换，避免并发读到半成品 |

### 1.5 验证

- `pytest`：**399 passed**（基线 365；新增 34 个回归用例）。
- 离线 eval：8/8 通过。
- 代码硬指标：违规总数 399 → 389，本轮未新增违规。

## 2. 规划：剩余缺口

按优先级排列。

### P0：上生产前必须完成

1. **分布式限流**：当前为单进程内存限流，多 worker 时每个进程各算一份。改为 Redis 滑动窗口（`REDIS_URL` 已有），飞书 nonce 缓存同步迁移。
2. **索引持久化**：重启时从对象存储重建能用但随文档量线性变慢。默认部署接入 Chroma 持久化（`CHROMA_PERSIST_DIR`）并把 BM25 语料落库，启动只加载、不重切分。
3. **Alembic 补全核心表**：现有迁移只覆盖 10 月新增的表，`users`/`tickets` 等核心表依赖 `create_all`。需要一条基线迁移，生产只用 `alembic upgrade head`。
4. **真实 IdP 与连接器验收**：OIDC、订单查询、退款都只有 mock/本地实现，需在部署环境验收。

### P1：可靠性

5. **事务性发件箱**：通知现在是“提交后发送”，进程在两者之间崩溃会漏发。改为 outbox 表 + worker 投递，保证至少一次。
6. **后台任务结果推送**：服务任务完成后没有 WS 广播，前端只能轮询。
7. **跨会话续办与外部事件唤醒**：任务运行时有检查点，但人工接单、外部回调还不能自动唤醒任务。
8. **统一异常策略**：`app/` 内仍有 33 处 `except Exception`（ruff BLE001），逐步改为具体异常或直接上抛。

### P2：性能与成本

9. `ChatService.add_message` 每次 `flush + refresh`，一轮多次往返；多数 `refresh` 可省。
10. 检索缓存是进程内 TTL 60 秒，多 worker 命中率低，换 Redis。
11. 默认聊天任务没有费用上限与截止时间，`max_answer_chars` 同时充当 `max_tokens`。
12. 存量代码硬指标违规 389 处（主要是测试中的魔数与长函数），按“改到哪个文件就收敛哪个文件”的规则清理。
