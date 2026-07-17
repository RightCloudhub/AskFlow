# 记忆与可观测

> 产品对齐：PRD §4.5/4.15（会话状态）、§4.12/4.17、§8.3；架构 `context-engineering.md`、`docs/observability/*`。  
> **记忆** = Agent 下一跳能合法看见的状态；**可观测** = 人与系统能解释「为何如此答、花了多少、哪里坏了」。

---

## 1. 总览

```
                    ┌──────── Memory ────────┐
 用户消息 ─────────►│ 工作记忆 · 情节存储     │
                    │ 槽位 · 检索证据（瞬时）  │
                    └───────────┬────────────┘
                                │ 组装进 Loop / RAG
                                ▼
                           决策与生成
                                │
                    ┌───────────▼────────────┐
                    │ Observability          │
                    │ logs · metrics · trace │
                    │ health · (cost 可选)   │
                    └────────────────────────┘
```

原则：

1. **记忆有边界** — 窗口物理上限；默认无跨会话「用户画像长期记忆」  
2. **写主路径、观旁路** — 聊天成功优先于 trace/成本落库  
3. **可解释** — 至少能回答：路由？拒答原因？用了哪些来源？哪次工具失败？  

---

## 2. 记忆分层

| 层 | 名称 | 存什么 | 生命周期 | 谁读写 |
|----|------|--------|----------|--------|
| M0 | **瞬时工作集** | 本轮 rewrite、检索 hits、grounding 分、工具结果 | 单 run | 内存 / run 内 |
| M1 | **会话工作记忆** | 最近 N 条消息、pending 槽位、会话 status | 会话存活 | PG metadata + messages |
| M2 | **情节存储** | 全量消息、工单、handoff session | 业务保留期 | PG |
| M3 | **知识记忆** | 文档 chunk / 向量 / BM25 | 随索引 generation | 向量库 + 对象存储 |
| M4 | **运营记忆** | Prompt 版本、意图映射、Gap/Draft | 长期 | PG |
| M5 | **长期用户记忆** | 偏好、跨会话事实 | — | **默认不做** |

### 2.1 M1 会话工作记忆（实现焦点）

| 组件 | 规则 |
|------|------|
| 消息历史 | 进入模型前裁剪：默认最多 **12** 条，单条 **~1200** 字 |
| 角色 | 仅 `user`/`assistant`；`staff` **镜像**为 assistant（暖回流） |
| 槽位 | `metadata.pending_tool` **merge-patch**，禁止整表覆盖 |
| 会话状态 | `active` → AI；`transferred` → 不进 AI；`closed` → 结束 |
| 指代改写 | 可选拼接最近 1 条 user（规则），不另建记忆库 |

### 2.2 状态切换时的记忆行为

| 事件 | 记忆动作 |
|------|----------|
| 转人工入队 | 最近 N 条 + 意图历史进 handoff payload；摘要失败则空 |
| 坐席回复 | 落库 role=staff；回流后镜像进 AI 历史 |
| 超时回 AI | 会话 `active`；用户可见超时/建单信息 |
| 工具成功 | 清 pending 槽位 |
| 弃槽 | 清 pending，按新意图走 |

### 2.3 明确不做什么

| 不做 | 原因 |
|------|------|
| 默认跨会话长期记忆 | 隐私、错误记忆、合规成本 |
| 把审计日志当对话记忆 | 职责混乱 |
| 无裁剪全量历史进 classify | 延迟与注入面 |
| 语义缓存当记忆复用政策答 | 时效风险 |

---

## 3. 记忆 → 上下文组装（与可观测交界）

组装顺序（简化）：

```
L0 Harness 常量
L1 运营 Prompt（active 版本）
L2 裁剪后历史（M1）
L3 本轮证据/工具结果（M0）
L4 当前问题（original + rewritten）
```

每次 run 产出 **ContextTrace**（可只打日志）：

```json
{
  "run_id": "...",
  "trace_id": "...",
  "route": "rag",
  "intent": "faq",
  "history": {"raw_count": 30, "used_count": 12, "staff_mirrored": 1},
  "query": {"original": "...", "rewritten": "...", "strategy": "rule"},
  "retrieval": {"fused": 6, "grounding_score": 0.62},
  "flags": [],
  "model": {"purpose": "rag_generate", "name": "..."},
  "usage": {"prompt_tokens": 0, "completion_tokens": 0}
}
```

脱敏后写入；失败不影响回复。

---

## 4. 可观测三支柱（MVP 最小集）

### 4.1 Logs

| 要求 | 说明 |
|------|------|
| JSON 结构化 | `ts, level, msg, trace_id, run_id, route, intent…` |
| mask | 默认开 |
| 里程碑 | auth、route、refusal、tool_error、handoff_timeout、index_fail |
| 禁止 | 完整 JWT、密钥、未脱敏长 prompt（生产） |

### 4.2 Metrics（先注册这些）

| 类别 | 最小指标 |
|------|----------|
| 流量 | `http_requests`、`ws_connections`、`chat_turns{route}` |
| 延迟 | `ttft_seconds`、`llm_latency{purpose}`、`retrieval_latency` |
| 质量代理 | `rag_refusal{reason}`、`harness_block{reason}`、`feedback{up\|down}` |
| 依赖 | `dependency_up`、`order_webhook{status}`、`llm_error{purpose}` |
| 队列 | `handoff_timeout`、`index_queue_depth`、`handoff_queue_depth` |

完整表见 `metrics-catalog.md`；**禁止** `user_id` 作 label。

### 4.3 Trace

| ID | 含义 |
|----|------|
| `trace_id` | 一次 HTTP/WS 逻辑请求 |
| `run_id` | 一轮用户消息的 Agent 处理 |

逻辑 stage（日志字段即可，不必上 OTel）：  
`prepare` → `intent` → `route` → `rewrite` → `retrieve` → `grounding` → `generate|tool` → `finalize`。

### 4.4 Health

`GET /health`：PG / Redis / 向量 / 对象存储；critical 失败 → **503**。  
LLM 探活 **不**作为 ready 硬依赖（避免外部抖动踢光实例）。

---

## 5. 记忆相关可观测（专项）

用数据证明「记忆策略在工作」：

| 信号 | 含义 | 动作 |
|------|------|------|
| `history_truncated` flag 升高 | 会话很长或单条爆 | 检查是否需摘要（后置）或引导新会话 |
| `staff_mirrored` 后质量差 | 镜像策略/裁剪切掉关键结论 | 调 N 或摘要 handoff |
| 槽位 `abandon` 高 | 用户常改口 | 正常；若乱弃查意图置信 |
| 槽位追问轮次顶满 | 用户不给单号 | 文案与转人工入口 |
| grounding 低 + 同问重复 | 知识缺口 | Gap 雷达 |
| transferred 仍出现 generate | **事故** | 立刻修状态机 |

Admin 最小：intent 分布、拒答 reason、👎、索引 pending 年龄、handoff 超时计数。  
成本/Run 回放 UI：**非 MVP 阻塞**；有日志即可。

---

## 6. 质量与记忆闭环

```
在线：👎 / 拒答 / handoff / clarify
  → Gap 信号（best-effort）
  → 运营补 Draft → 索引（M3 更新）
  → 离线 golden / refusals 回归
```

记忆（知识）更新后应用 **generation 世代**，避免检索黑洞（write-new-then-delete）。

---

## 7. 隐私交线

| 场景 | 策略 |
|------|------|
| 日志中的订单号/手机 | mask |
| 坐席看历史 | 业务需要，权限内 |
| 导出/删除权 | v2 |
| 长期记忆产品 | 默认无；若做须单独同意与开关 |

---

## 8. MVP 验收

**记忆**

- [ ] 历史超限只送预算内消息（trace `used_count`）  
- [ ] staff 回流后 AI 可见镜像历史  
- [ ] 槽位 merge-patch，不丢其他 metadata  
- [ ] transferred 不把用户句送进模型  
- [ ] 无跨会话长期记忆默认行为  

**可观测**

- [ ] 每条业务日志可关联 `trace_id`  
- [ ] `/health` 依赖挂 → 503  
- [ ] `/metrics` 含 TTFT、拒答、webhook、handoff_timeout  
- [ ] 弱拒答 run 可从日志看出 `reason=weak_evidence` 且无 generate  
- [ ] PII 样例日志已脱敏  

---

## 9. 与目录映射

| 能力 | 代码落点（规划） |
|------|------------------|
| 历史裁剪 / 组装 | `services/rag/context/` |
| 槽位 | `services/agent/slots/` |
| 会话状态 | `services/chat/session/` |
| Harness flags | `services/agent/harness/` |
| metrics 中间件 | `middleware/`、`api/v1/health` |
| Gap 信号 | `services/knowledge/gap/` |

---

## 10. 延后（有意不进 MVP）

| 项 | 何时 |
|----|------|
| OpenTelemetry 全链路 | 多服务后再说 |
| Agent Run 回放 Admin | 日志不够用时 |
| 会话中段自动摘要 | 长会话成痛点时 |
| 精确美元成本看板 | 有价目表与优化波次时 |
| 用户级长期记忆 | 隐私评审后 |

相关：`security-and-fallback.md`（失败时记忆与展示）、`performance.md`（记忆预算即性能预算）、`observability/monitoring.md`。
