# 查询改写（Query Rewrite）

> 对应 PRD §4.2 检索、§4.3 意图、§4.4 槽位、P3「关键词检索无法理解自由表述」。  
> 代码落点：`apps/api/app/services/rag/query_rewrite/`。  
> 依赖：[context-engineering.md](./context-engineering.md)、[rag-pipeline.md](./rag-pipeline.md)。

---

## 1. 为什么需要改写

| 用户原话 | 问题 | 改写目标 |
|----------|------|----------|
| 「那个怎么退啊」 | 指代消解缺失 | 「退货政策 / 退货流程」 |
| 「物流到哪了」 | 缺订单号，且偏口语 | 检索侧：「物流 查询 快递 状态」；槽位侧仍追问 order_id |
| 「VIP 包邮吗」 | 同义 / 产品黑话 | 对齐知识库用语「会员 免运费」 |
| 「转人工！！！」 | 非检索意图 | **跳过**检索改写，走 handoff 路由 |

**原则：改写服务检索与分类，不替代路由，不编造业务事实。**

---

## 2. 在流水线中的位置

```
WS message
  → Harness.prepare（空/过长/注入）
  → 槽位续跑？ ──是──► 跳过分类与（可选）改写，直跑 tool
  │
  → 意图分类（可用 original；规则侧可同时看 rewrite）
  → Harness.choose_route
  → route == rag？
        │
        ├─ 是 → QueryRewrite → BM25(rewritten) + Vector(rewritten)
        │         可选：BM25 同时带 original 双通道
        └─ 否 → 不改写或仅轻量规范化
```

| 路由 | 是否改写 | 说明 |
|------|----------|------|
| `rag` | **是** | 主路径 |
| `tool` | 可选规范化 | 订单号抽取优先于语义改写 |
| `ticket` / `handoff` / `clarify` | **否**（或仅 strip） | 避免改写改变投诉/转人工语义 |

---

## 3. 策略分层（由便宜到昂贵）

### 3.1 L0 规范化（必做，零 LLM）

| 步骤 | 行为 |
|------|------|
| Unicode / 空白 | NFKC、合并空白、去首尾 |
| 长度 | 超过 `REWRITE_MAX_INPUT_CHARS`（建议 500）截断 |
| 控制字符 | 剔除 |
| 大小写 | 保留中文；英文订单号等保持原样 |

输出：`normalized_query`。任何后续策略失败都回落此层。

### 3.2 L1 规则改写（MVP 推荐默认开启）

| 规则类型 | 示例 | 动作 |
|----------|------|------|
| 指代表达 | 「这个」「那个」「刚才」 | 拼接最近 1 条 user 问题关键词（简单拼接，不做 LLM） |
| 同义扩展 | 退货↔退换、物流↔快递↔运单 | 检索用 query 追加同义词（配置表） |
| 领域词典 | SKU / 产品线别名 | 别名 → 标准名 |
| 噪声剥离 | 「在吗」「谢谢」「你好」单独成句 | 纯寒暄 → 不改写，可走 clarify 或短答 |
| 注入残留 | 已被 Harness 拦截的不进入 | — |

配置建议：

- `query_synonyms.yaml` 或 DB 表（可热更，Admin 后期再做 UI）  
- 规则命中写 `rewrite_strategy=rule` + `rules_fired[]`

### 3.3 L2 LLM 改写（可选，默认关或仅低分触发）

**触发条件（建议 AND/OR 可配）：**

- 向量/ BM25 预检 top1 分过低（需二次检索时）  
- 原句过短（如 &lt; 6 字）且非槽位  
- 显式配置 `REWRITE_LLM_ENABLED=true`

**Prompt 约束（硬性）：**

```text
你只输出一行检索用查询，不要回答问题，不要编造政策/价格/订单状态。
保留实体：订单号、错误码、产品名。
语言与用户一致。
```

| 旋钮 | 建议默认 |
|------|----------|
| `REWRITE_LLM_TIMEOUT_MS` | 800 |
| `REWRITE_LLM_MAX_TOKENS` | 64 |
| 失败 | 回落 L1/L0，flag `rewrite_llm_failed` |
| 输出校验 | 空 / 过长 / 含「根据我的知识」等 → 丢弃 |

**禁止：** 用改写模型直接生成最终答案；改写结果不展示给用户（用户侧仍显示原问）。

### 3.4 L3 HyDE / 多查询（v1.5+，非 MVP）

- 假设文档生成 / multi-query 融合  
- 成本高，须独立 eval 门禁  
- 目录预留：`query_rewrite/hyde.py`、`multi_query.py`

---

## 4. 双通道检索约定

MVP 推荐：

```
BM25  ← rewritten (+ 可选 original 二次召回取并集)
Vector ← rewritten 的 embedding
Fusion ← RRF / 加权
```

| 模式 | 适用 |
|------|------|
| `rewrite_only` | 默认；简单 |
| `rewrite_and_original` | 规则改写激进时防丢关键词 |
| `original_only` | 调试 / 回滚开关 |

配置：`RETRIEVAL_QUERY_MODE=rewrite_only|rewrite_and_original|original_only`

---

## 5. 与意图 / 槽位的边界

```
                    ┌─ handoff / ticket 关键词共现 ─► 不改写语义
用户句 ─► 规则意图 ─┤
                    └─ order_query ──────────────► 优先正则抽 order_id
                                                   有号：tool；无号：追问
                                                   检索改写仅用于 search_knowledge
```

- **槽位续跑**：用户句是「AB12345678」→ 不做 FAQ 式改写  
- **分类输入**：默认用 `original`；规则词典可同时匹配 `normalized`  
- **handoff 共现规则**：必须在 original 上判定，避免改写抹掉「转人工」  

---

## 6. 数据契约

```python
class RewriteResult(TypedDict):
    original: str
    normalized: str
    rewritten: str
    strategy: Literal["none", "normalize", "rule", "llm"]
    rules_fired: list[str]
    latency_ms: int
    flags: list[str]
```

写入 `ContextTrace.query`（见上下文工程文档 §7）。

---

## 7. 配置项（附录级）

| 配置 | 默认 | 说明 |
|------|------|------|
| `REWRITE_ENABLED` | true | 总开关 |
| `REWRITE_LLM_ENABLED` | false | MVP 建议关 |
| `REWRITE_MAX_INPUT_CHARS` | 500 | |
| `REWRITE_SYNONYM_PATH` | `data/query_synonyms.yaml` | |
| `REWRITE_COREFERENCE_LOOKBACK` | 1 | 指代拼接看最近几条 user |
| `RETRIEVAL_QUERY_MODE` | `rewrite_only` | |

---

## 8. 评测与回归

| 用例集 | 目录 | 断言 |
|--------|------|------|
| 同义 / 口语 | `evals/golden/faq` | rewrite 后 recall@k 不下降 |
| 指代 | `evals/golden/faq` | 「那个」+ 上文 → 命中正确 doc |
| 拒答不误伤 | `evals/refusals` | 改写不得把无依据问句「改成」有文档的假问题 |
| 转人工 | 集成测 | 「我要转人工」route=handoff，且 rewrite 不抹动词 |
| 订单号 | `evals/golden/order` | 纯单号不 LLM 改写 |

**红线：** 改写不得降低拒答率来「提高解答率」（防止为指标牺牲 Honest RAG）。

---

## 9. 监控指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `askflow_rewrite_total` | counter | labels: strategy, status |
| `askflow_rewrite_latency_seconds` | histogram | |
| `askflow_rewrite_llm_fail_total` | counter | |
| `askflow_retrieval_mode` | counter | rewrite_only / … |

告警建议：`rewrite_llm_fail` 5m 错误率 &gt; 20% → warning（自动回落时可不 page）。

---

## 10. 验收要点

| # | 标准 |
|---|------|
| 1 | 关闭 `REWRITE_ENABLED` 后检索仍可用（original） |
| 2 | LLM 改写超时不影响主路径 P95 目标（回落） |
| 3 | trace 可区分 original / rewritten |
| 4 | handoff / 注入句不被改写成可检索 FAQ |
| 5 | 同义规则可在不发版情况下更新（文件或配置，MVP 文件即可） |
