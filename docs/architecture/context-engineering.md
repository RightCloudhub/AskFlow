# 上下文工程（Context Engineering）

> 对应 PRD §3.2 流水线、§4.2.1 历史裁剪、§4.3.3 Harness、§4.7 暖回流、§4.10 Prompt 组装。  
> 代码落点：`apps/api/app/services/rag/context/`、`services/agent/harness/`、`services/prompt/`。

---

## 1. 目标与原则

| 原则 | 说明 |
|------|------|
| **证据优先于流畅** | 进入生成的上下文必须可追溯到检索 chunk 或工具结果；禁止用闲聊补齐政策/价格 |
| **预算可控** | 历史、证据、系统提示有硬上限；超限先裁后生成，不交给模型「自己看着办」 |
| **角色合法** | 仅 `user` / `assistant`（含 staff 镜像）进入 LLM 历史；非法 role 丢弃 |
| **失败可降级** | 摘要失败、证据自检超时不阻塞主流程；打 flag 供监控与 Gap 雷达 |
| **安全不进运营模板** | Harness 注入拒绝文案、截断提示等写死在代码常量 |

**上下文工程 = 在有限 token 预算内，组装「足够回答当前问题」的最小充分信息集。**

---

## 2. 上下文分层模型

单次用户消息进入 Agent 后，上下文分五层组装：

```
┌─────────────────────────────────────────────────────────┐
│ L0  系统层（不可运营改关键安全段）                          │
│     harness 安全策略 · policy_version · 角色约束          │
├─────────────────────────────────────────────────────────┤
│ L1  运营 Prompt（可热更）                                 │
│     rag.system / intent.classifier / agent.clarify …     │
├─────────────────────────────────────────────────────────┤
│ L2  会话历史（裁剪后）                                     │
│     最近 N 轮 · 单条截断 · staff→assistant 镜像            │
├─────────────────────────────────────────────────────────┤
│ L3  检索 / 工具证据                                       │
│     ranked chunks · 工具 JSON · 弱证据拒答不进生成        │
├─────────────────────────────────────────────────────────┤
│ L4  当前用户问题（改写后 query + 原始 query）               │
│     槽位续跑时附带 pending_tool 元数据                     │
└─────────────────────────────────────────────────────────┘
```

| 层 | 可变主体 | 热更新 | 失败策略 |
|----|----------|--------|----------|
| L0 | 代码常量 + Harness | 否（发版） | 硬停 / 固定话术 |
| L1 | Prompt 版本表 | 是 | 回落代码常量 |
| L2 | 消息存储 | — | 裁剪 / 丢弃非法 |
| L3 | 检索 / webhook | — | 拒答或 mock 降级 |
| L4 | 用户输入 + rewrite | rewrite 可配置 | 用原始 query 兜底 |

---

## 3. 会话历史策略

### 3.1 默认预算（可配置，须进 eval）

| 旋钮 | 建议默认 | 说明 |
|------|----------|------|
| `CONTEXT_MAX_TURNS` | 12 | 进入模型的最大消息条数（user+assistant 合计） |
| `CONTEXT_MAX_CHARS_PER_MSG` | 1200 | 单条字符上限，超出尾部截断并打标 `history_truncated` |
| `CONTEXT_MAX_TOTAL_CHARS` | 8000 | 历史合计软上限；先丢最旧轮 |
| `CONTEXT_KEEP_SYSTEM_HINT` | false | MVP 不把 system 消息塞进多轮历史 |

### 3.2 裁剪算法（确定性）

```
1. 从 durable 消息存储取会话历史（按 created_at ASC）
2. 过滤：role ∉ {user, assistant, staff} → 丢弃
3. staff → 镜像为 assistant（暖回流可见人工结论，PRD §6.3）
4. 自尾向头取，直到触达 MAX_TURNS 或 TOTAL_CHARS
5. 单条超长 → 截断并 flag
6. 输出：List[{role, content}] + ContextTrace
```

**禁止：**

- 整表覆盖会话 `metadata`（槽位等用 merge-patch）
- 把 `system` / 审计 / 内部备注塞进用户可见或 LLM 历史
- 在 `transferred` 状态下仍把用户消息送入 AI 上下文

### 3.3 状态与历史关系

| 会话状态 | 用户消息 | 是否进入 Agent 上下文 |
|----------|----------|----------------------|
| `active` | 落库 + 流水线 | 是 |
| `transferred` | 落库 + 推坐席 | **否** |
| `closed` | 拒绝新消息（或仅只读） | 否 |
| `returned` 后 `active` | 正常 | 是（含镜像后的 staff 历史） |

---

## 4. 检索证据上下文（RAG）

### 4.1 组装结构（`rag.context` 模板变量）

```text
## 证据
[1] (source={doc_title}, score={s})
{chunk_text}

[2] ...
## 用户问题
{question}                    # 优先 rewritten；可附 original
```

| 旋钮 | 建议默认 | 说明 |
|------|----------|------|
| `RAG_MAX_CHUNKS` | 6 | 进入 Prompt 的 chunk 数 |
| `RAG_MAX_CHARS_PER_CHUNK` | 800 | chunk 截断 |
| `RAG_INCLUDE_WEAK_ON_REFUSAL` | 2 | 拒答时最多展示弱来源数（**不调 LLM**） |
| `RAG_CITATION_STYLE` | `[n]` | 与 `sources[].index` 对齐 |

### 4.2 证据选择顺序

```
融合排序结果
  → 按 score / channel 归一化
  → grounding 阈值过滤
  → 去重（同 doc 相邻 chunk 可合并，MVP 可跳过）
  → 截断到 MAX_CHUNKS / 总字符预算
  → 编号 1..n 写入 sources[]
```

弱证据拒答路径：**不组装 L1 生成 Prompt，不调用 LLM**；只返回固定话术 + 弱 sources。

### 4.3 与生成解耦

| 产物 | 消费者 |
|------|--------|
| `sources[]` | WS `source` 帧 + 前端侧栏 + 引用自检 |
| `context_block` | `rag.context` 渲染 |
| `grounding_score` | 拒答决策 + `message_end.answer_confidence` |
| `retrieval_trace` | 监控、Gap 雷达、Dashboard |

---

## 5. 工具与槽位上下文

订单等工具不走 RAG 证据块，走 **结构化结果上下文**：

```json
{
  "tool": "search_order",
  "args": {"order_id": "AB12345678"},
  "result": {"status": "...", "tracking": "...", "data_source": "webhook|mock"},
  "pending_slot": null
}
```

| 场景 | 上下文行为 |
|------|------------|
| 缺槽位 | 不调工具；澄清话术；`metadata.pending_tool` 挂起 |
| 续跑命中 | 跳过分类；工具结果进本轮 assistant 上下文 |
| webhook 失败 | mock + `data_source=mock` + 指标；**禁止假装真实订单** |
| 弃槽 | 清 pending；按新意图重组上下文 |

---

## 6. Prompt 渲染与变量契约

### 6.1 MVP 模板 Key（PRD §4.10.2）

| Key | 必填变量 | 用途 |
|-----|----------|------|
| `rag.system` | （可选 policy 声明） | 系统角色、引用规则 |
| `rag.context` | `chunks`, `question` | 证据 + 问题 |
| `rag.fallback_no_results` | — | 无结果话术 |
| `rag.fallback_llm_down` | — | LLM 宕机 |
| `intent.classifier` | `messages`, `intent_labels` | 分类 |
| `agent.clarify` | `reason`（可选） | 澄清 |

### 6.2 渲染规则

1. DB active 版本优先 → 失败回落代码常量  
2. 占位符缺失 → 拒绝发布（Admin 校验）或运行时回落  
3. 渲染后总长度再做一次截断（`OUTPUT` 侧由 Harness finalize）  
4. **禁止**把 Harness 安全拒答文案做成可运营模板  

### 6.3 版本与可追溯

每次 run 记录：

```text
prompt_key → version_id → policy_version(harness) → rewritten_query_hash
```

供审计回滚与「改话术是否变差」对比。

---

## 7. ContextTrace（实现必写）

每个 run 产出结构化 trace（与 PRD harness trace 合并）：

```json
{
  "run_id": "uuid",
  "trace_id": "uuid",
  "conversation_id": "...",
  "policy_version": "harness-1.0",
  "history": {
    "raw_count": 40,
    "used_count": 12,
    "truncated_msgs": 1,
    "staff_mirrored": 2
  },
  "query": {
    "original": "...",
    "rewritten": "...",
    "rewrite_strategy": "rule|llm|none",
    "rewrite_latency_ms": 12
  },
  "retrieval": {
    "bm25_hits": 8,
    "vector_hits": 10,
    "fused": 6,
    "grounding_score": 0.62,
    "filters": {}
  },
  "budget": {
    "prompt_chars": 5200,
    "max_output_tokens": 1024
  },
  "flags": ["history_truncated"],
  "route": "rag",
  "intent": "faq"
}
```

- **落库：** best-effort（可进 analytics 表或日志）；失败不影响聊天  
- **脱敏：** 写入前 mask PII（与 §4.11 一致）  
- **消费方：** Dashboard、Gap 雷达、eval 归因、告警  

---

## 8. 与目录映射

| 模块 | 路径 |
|------|------|
| 历史裁剪 / 组装 | `services/rag/context/` |
| 查询改写 | `services/rag/query_rewrite/`（见 [query-rewrite.md](./query-rewrite.md)） |
| Grounding | `services/rag/grounding/` |
| Prompt 渲染 | `services/prompt/renderer/` |
| Harness | `services/agent/harness/` |
| 流水线编排 | `services/agent/pipeline/` |

---

## 9. 验收要点

| # | 标准 | 验证 |
|---|------|------|
| 1 | 历史超过 12 条时只送最近预算内消息 | 单测 + trace.history.used_count |
| 2 | staff 消息回流后 AI 可见 | 集成：resolve(returned) 后追问 |
| 3 | 弱证据不调 LLM | mock LLM 调用计数 = 0 |
| 4 | transferred 不进 AI | WS 断言无 token 帧 |
| 5 | Prompt 热更后新会话用新版本 | 双实例 + 缓存失效 |
| 6 | ContextTrace 含 rewrite / retrieval 字段 | 日志或 analytics 抽检 |

---

## 10. 后续增强（非 MVP 阻塞）

| 项 | 说明 | 分期 |
|----|------|------|
| 会话摘要压缩 | 超长会话用摘要替换中段历史 | v1.5+ |
| 证据 MMR 去重 | 降低同文档重复 chunk | v1.5 |
| 多 Bot 知识子集 | 按业务线过滤 L3 | 远期 E18 |
| 用户长期记忆 | 默认不做；隐私成本高 | 不在范围 |
