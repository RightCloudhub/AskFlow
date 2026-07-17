# Honest RAG 全链路

> 对应 PRD §4.2、§1.4 G1。  
> 串联：[query-rewrite.md](./query-rewrite.md) → 检索 → grounding → 生成 → 引用自检。  
> 代码：`apps/api/app/services/rag/*`。

---

## 1. 端到端流程

```
question (original)
  → QueryRewrite → rewritten
  → BM25(rewritten [, original])
  → Vector(embed(rewritten))
  → Fusion (+ optional rerank hook)
  → Filter (sources / doc_ids / time)
  → Grounding 评估
       ├─ fail → 弱证据拒答（不调 LLM）+ 最多 N 弱来源 + gap 信号
       └─ pass → Prompt 组装 (rag.system + rag.context)
                 → 流式生成
                 → 引用自检 [n] ↔ sources
                 → 截断 / 空输出 Harness
                 → message_end(confidence, verification, sources)
```

---

## 2. 模块职责

| 目录 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `query_rewrite/` | 规范化 / 规则 / 可选 LLM | original + 短历史 | RewriteResult |
| `bm25/` | 关键词召回 | query | hits[] |
| `vector/` | 语义召回 | embedding(query) | hits[] |
| `fusion/` | RRF/加权 + rerank hook | multi-channel hits | ranked[] |
| `grounding/` | 阈值与最少命中 | ranked | score + refuse? |
| `context/` | 历史 + 证据块组装 | msgs + chunks | prompt messages |
| `generator/` | 流式 LLM | prompts | token stream |
| `citations/` | 行内引用校验 | text + sources | verification |

---

## 3. Grounding 默认旋钮

| 参数 | 默认 | 含义 |
|------|------|------|
| 证据置信度阈值 | 0.35 | 低于则拒答 |
| 最少命中数 | 1 | 零命中无条件拒答 |
| 拒答仍展示来源数 | 2 | UX：引导换问法 / 转人工 |

归一化：各通道分数映射到 0–1 再融合；**禁止**用生成模型自觉「我很有信心」代替 grounding。

---

## 4. Chunk 元数据契约

```json
{
  "doc_id": "...",
  "source": "filename or title",
  "generation": 3,
  "indexed_at": "ISO-8601",
  "chunk_index": 0,
  "text": "..."
}
```

- 索引 **write-new-then-delete**（generation 世代）防检索黑洞  
- 过滤启用前旧 chunk 须补齐 metadata  

---

## 5. 流式与取消

- token 帧经 WS 推送  
- `cancel` → 协作取消 LLM 流（单 worker MVP；多 worker 见 tracing 多实例方案）  
- 超输出上限：截断 + 提示 + metrics `truncated`  

---

## 6. 故障话术

| 条件 | 模板 Key / 行为 |
|------|-----------------|
| 零命中 / 弱证据 | 固定拒答 + 弱来源（不调 LLM） |
| LLM 宕机 | `rag.fallback_llm_down` |
| 空输出 | Harness 兜底话术（不可运营改） |

---

## 7. 与评测

| 集 | 覆盖 |
|----|------|
| `evals/golden/*` | FAQ 命中、引用有效 |
| `evals/refusals/*` | 弱证据、注入、域外 |

CI 门禁目标：v1.5+；MVP 先本地 runner。

---

## 8. 配置速查

| 配置 | 默认 |
|------|------|
| `RAG_MAX_CHUNKS` | 6 |
| `GROUNDING_THRESHOLD` | 0.35 |
| `GROUNDING_MIN_HITS` | 1 |
| `REFUSAL_SHOW_SOURCES` | 2 |
| `CHUNK_SIZE` / `OVERLAP` | 500 / 50 |
| `REWRITE_ENABLED` | true |
