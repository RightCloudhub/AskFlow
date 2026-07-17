# 链路追踪与 Run Trace

> 对应 PRD §3.2、§4.3.3 harness trace、§4.11 `trace_id`。  
> MVP 以 **应用内 ContextTrace + 结构化日志** 为主；OpenTelemetry 为可选增强。

---

## 1. ID 模型

| ID | 作用域 | 生成 | 传播 |
|----|--------|------|------|
| `trace_id` | 一次 HTTP 或 WS 连接上的逻辑请求 | middleware / WS auth 后 | 日志、审计、响应头 `X-Trace-Id` |
| `run_id` | 一次用户消息的 Agent 流水线 | pipeline 入口 | ContextTrace、message metadata |
| `conversation_id` | 会话 | 已有实体 | 全程 |
| `message_id` | 单条消息 | 落库后 | `message_end` 帧 |

关系：

```
trace_id  1──* run_id（长连接上多轮）
run_id    1──1  user message turn
run_id    1──* 子步骤 span（逻辑）
```

---

## 2. 逻辑 Span 列表（MVP）

不必上完整 OTel，但日志/trace 对象应按阶段打点：

| span / stage | 关键字段 |
|--------------|----------|
| `harness.prepare` | flags, blocked_reason |
| `slot.resume` | hit, abandoned |
| `intent.classify` | intent, confidence, source |
| `route.decide` | route, forced |
| `rewrite` | strategy, latency_ms |
| `retrieve.bm25` | hits, latency_ms |
| `retrieve.vector` | hits, latency_ms |
| `retrieve.fuse` | fused, top_score |
| `grounding` | score, refuse |
| `llm.generate` | tokens, latency, truncated |
| `citation.verify` | ok / oob / skipped |
| `tool.execute` | tool, status, data_source |
| `ticket.create` | id, deduped |
| `handoff.enqueue` | summary_failed |
| `gap.signal` | types, ok |
| `harness.finalize` | empty_output, truncated |

每个 stage：`start_ts`、`duration_ms`、`error`（可选）。

---

## 3. ContextTrace 存储策略

| 方案 | MVP | 说明 |
|------|-----|------|
| 结构化日志一行 JSON | ✅ | 必须 |
| PG `run_traces` 表 | 可选 | 便于 Admin 钻取；TTL 7–30 天 |
| Redis 仅热数据 | 可选 | 不持久 |
| OTel → Jaeger/Tempo | v1.5+ | 采样率可配 |

**体积控制：** 不存完整 prompt / 完整 chunk 正文；存 hash、分数、doc_id、flags。

---

## 4. 与审计的区别

| | Trace | AuditLog |
|--|-------|----------|
| 主体 | 系统决策过程 | 人的变更操作 |
| 频率 | 每轮对话 | 配置/知识变更 |
| 失败 | best-effort | 与业务同事务 |

---

## 5. 多 Worker 注意（Wave E）

| 问题 | 方向 |
|------|------|
| WS cancel 打到其他实例 | Redis pub/sub 广播 cancel(run_id) |
| metrics 多进程 | `prometheus_client` multiprocess mode 或侧车 |
| trace 拼接 | 统一 `trace_id` 经 Redis/消息传递 |

试点单 worker 时文档写明限制即可。

---

## 6. 前端可见性

MVP：

- 不暴露完整 trace  
- `message_end` 带 `answer_confidence`、`verification`、sources  

Admin（可选 v1.5）：

- 按 `run_id` / `conversation_id` 查看 route、refusal reason、rewrite  
