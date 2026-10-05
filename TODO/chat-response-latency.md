# TODO: 聊天回答慢的优化

状态：待办
创建：2026-10-04
关联日志：`POST /v1/embeddings` ×2 → `POST /v1/chat/completions`（WS 会话）

## 日志时间线还原

| 时间 | 事件 | 耗时 |
| --- | --- | --- |
| 21:32:45.696 | WS accepted | — |
| 21:33:12.259 | embedding #1 | 之前 26.6s 无服务端 HTTP |
| 21:33:14.055 | embedding #2 | 1.80s |
| 21:33:18.116 | chat/completions 200 | 4.06s |

结论：服务端真实处理约 6 秒。26s 空档内只做了 DB 读取 + 纯规则意图识别
（`IntentClassifier` 默认不起 LLM），不可能是服务端瓶颈，基本是用户输入/前端等待。
真正瓶颈是后面 ~6s。

## 待办项（按收益排序）

### P0：流式 token 被缓冲，整段生成完才发
- 位置：`apps/api/app/api/v1/chat/ws_handler.py:119-140`
- 现状：`on_token` 只 `emitted.append(chunk)`，`emit_turn` 在
  `handle_user_message` + `db.commit()` 全部结束后才逐条发 token。
- 影响：首字延迟 = 整段生成时间，是“感觉慢”的最大来源。
- 目标：`on_token` 直接 `ws.send_json({"type": "token", ...})`；
  `db.commit()` 挪到发送之后。
- 注意：`intent` / `source` 仍应尽量先发。建议新增与 `token_sink` 同款的
  `progress_sink`，在检索完成拿到 sources/intent 时回调一次，实现
  `intent → source → token(实时) → 落库 → message_end`。
- 前端：`apps/web/src/services/chat-ws.ts` 的 `dispatchFrame` 独立处理各 frame，
  可容忍顺序。

### P0：首个请求现场 embed 种子库
- 位置：`apps/api/app/services/rag/pipeline.py:108`（`ensure_seeded`）
- 现状：首次检索把 4 条 FAQ 全量 embed，日志里耗时约 1.8s。
- 目标：在 `apps/api/app/main.py` 的 `lifespan` 中启动预热：
  `await ensure_seeded()`，并预热 `get_default_bm25()` 与
  LLM/embedding 客户端，把冷启动成本挪到启动阶段。

### P1：每次外部调用新建 httpx.AsyncClient，无连接复用
- 位置：
  - `apps/api/app/services/rag/embedding/client.py` 的 `_request`
  - `apps/api/app/services/llm/client.py` 的 `_post_json` / `_iter_sse`
- 现状：每次调用重新 TCP + TLS 握手，每次白付数百 ms。
- 目标：改为进程级共享 client（lifespan 建、shutdown 时 `aclose`），
  或在 `get_embedder` / `get_llm_client` 单例内持有。

### P1：检索串行
- 位置：`apps/api/app/services/rag/pipeline.py:109-110`
- 现状：BM25（本地 CPU）与向量检索（网络）顺序执行。
- 目标：并发执行，省一次串行网络等待：
  ```python
  bm25_hits, vector_hits = await asyncio.gather(
      asyncio.to_thread(get_default_bm25().search, query, top_k),
      self.vector.search(query, top_k=top_k),
  )
  ```

### P2：DB 与缓存细节
- `ChatService.add_message` 每次 `flush()` + `refresh()`
  （`apps/api/app/services/chat/session/service.py:82-94`），一轮多次往返；
  多数 `refresh` 可省（flush 后主键已可用）。
- 检索缓存为进程内、TTL 60s（`apps/api/app/services/rag/retrieval_cache.py`），
  多 worker 命中率低，可换 Redis。
- `max_answer_chars=4000` 同时作为 `max_tokens`，生成越长越慢，按需调小。

### P2：模型与供应商
- 生成走 `api.mmkg.cloud`，4s 主要取决于该供应商首 token 与吞吐。
- 可换更快的模型 / 同区域部署。意图识别规则优先、LLM 未启用，无需改动。

## 验证方式
在 `handle_message` 开头/结尾加带 `trace_id` 的日志
（收到消息、检索完成、首 token、生成完成、commit 完成），
确认 26s 是用户侧还是服务端，并量化 P0/P1 收益。

## 约束
改动需满足仓库硬性指标：函数 ≤50 行、文件 ≤300 行、嵌套 ≤3 层、
位置参数 ≤3、圈复杂度 ≤10、禁止魔数。
