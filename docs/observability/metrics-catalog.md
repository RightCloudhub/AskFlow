# Metrics 目录（Prometheus）

> 命名前缀统一 `askflow_`。Histogram 单位秒；Counter 只增。  
> 暴露：`GET /metrics`（网络隔离，无鉴权）。

---

## 1. HTTP / 运行时

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_http_requests_total` | counter | method, route, status | 业务 REST |
| `askflow_http_request_duration_seconds` | histogram | method, route | |
| `askflow_http_rate_limited_total` | counter | scope=user\|ip | 429 |
| `askflow_process_info` | gauge | version, harness_policy | 常 1，标识版本 |
| `askflow_dependency_up` | gauge | name=postgres\|redis\|vector\|object_storage | 1/0 |

---

## 2. WebSocket / 聊天

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_ws_connections` | gauge | | 当前在线 |
| `askflow_ws_auth_failures_total` | counter | reason | |
| `askflow_ws_messages_total` | counter | direction=in\|out, type | |
| `askflow_ws_cancel_total` | counter | | 用户取消生成 |
| `askflow_chat_turns_total` | counter | route, intent | 完成一轮 |
| `askflow_ttft_seconds` | histogram | route | 首 token |
| `askflow_generate_duration_seconds` | histogram | route | 整轮生成 |

---

## 3. RAG / 检索 / 改写

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_rewrite_total` | counter | strategy, status | none/rule/llm × ok/fail |
| `askflow_rewrite_latency_seconds` | histogram | strategy | |
| `askflow_retrieval_total` | counter | channel=bm25\|vector\|fused | |
| `askflow_retrieval_latency_seconds` | histogram | channel | |
| `askflow_retrieval_hits` | histogram | channel | 命中条数分布 |
| `askflow_grounding_score` | histogram | | 0–1 分桶 |
| `askflow_rag_refusal_total` | counter | reason | weak_evidence / zero_hit / … |
| `askflow_rag_generate_total` | counter | status=ok\|fallback\|truncated | |
| `askflow_citation_verify_total` | counter | result=ok\|oob\|skipped | 引用自检 |
| `askflow_answer_confidence` | histogram | | 下发前端的置信度 |

---

## 4. Agent / Harness

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_intent_total` | counter | intent, source=rule\|llm\|fallback | |
| `askflow_intent_confidence` | histogram | intent | |
| `askflow_route_total` | counter | route, forced=true\|false | forced=Harness 改写 |
| `askflow_harness_block_total` | counter | stage, reason | prepare/choose_route/finalize |
| `askflow_harness_flag_total` | counter | flag | history_truncated 等 |
| `askflow_slot_events_total` | counter | event=ask\|fill\|abandon\|timeout | |

---

## 5. LLM / Embedding

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_llm_requests_total` | counter | purpose=chat\|classify\|rewrite\|summary, status | |
| `askflow_llm_latency_seconds` | histogram | purpose | |
| `askflow_llm_tokens_total` | counter | purpose, direction=prompt\|completion | |
| `askflow_llm_error_total` | counter | purpose, error_class | timeout/http/parse |
| `askflow_embedding_requests_total` | counter | status | |
| `askflow_embedding_latency_seconds` | histogram | | |

---

## 6. 工具 / Webhook

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_tool_calls_total` | counter | tool, status | |
| `askflow_tool_latency_seconds` | histogram | tool | |
| `askflow_order_webhook_total` | counter | status=ok\|timeout\|http_error\|mock | |
| `askflow_order_webhook_latency_seconds` | histogram | | |

---

## 7. Ticket / Handoff

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_ticket_created_total` | counter | type, source=agent\|user\|timeout | |
| `askflow_ticket_dedup_total` | counter | | 并发收敛到已有单 |
| `askflow_ticket_status_total` | counter | from, to | 状态迁移 |
| `askflow_handoff_created_total` | counter | | |
| `askflow_handoff_claim_total` | counter | result=ok\|conflict | 409 |
| `askflow_handoff_timeout_total` | counter | | 清扫升级 |
| `askflow_handoff_queue_depth` | gauge | | queued 数 |
| `askflow_handoff_pickup_seconds` | histogram | | created→claimed |

---

## 8. 知识索引 / Gap

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_index_jobs_total` | counter | status=success\|failed | |
| `askflow_index_job_duration_seconds` | histogram | | |
| `askflow_index_queue_depth` | gauge | | |
| `askflow_documents` | gauge | status | pending/indexing/active/failed/archived |
| `askflow_chunks_total` | gauge | | |
| `askflow_gap_signals_total` | counter | signal | clarify/rag_refusal/… |
| `askflow_gap_open` | gauge | | |
| `askflow_draft_transitions_total` | counter | to=approved\|rejected | |

---

## 9. 反馈 / 审计

| 指标 | 类型 | Labels | 说明 |
|------|------|--------|------|
| `askflow_feedback_total` | counter | value=up\|down\|neutral | |
| `askflow_audit_events_total` | counter | action | |

---

## 10. Histogram 桶建议

| 指标族 | buckets（秒） |
|--------|----------------|
| TTFT / HTTP | `0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 10` |
| LLM | `0.1, 0.5, 1, 2, 5, 10, 30` |
| Retrieval | `0.01, 0.05, 0.1, 0.25, 0.5, 1, 2` |
| Handoff pickup | `30, 60, 120, 300, 600, 1800` |

Grounding / confidence：用 `0.1, 0.2, …, 1.0` 或 Summary。

---

## 11. 标签基数红线

**禁止**高基数 label：`user_id`、`conversation_id`、`order_id`、原始 query。  
这些只进日志 / trace，不进 Prometheus labels。
