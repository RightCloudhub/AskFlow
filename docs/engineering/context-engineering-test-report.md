# 上下文工程完成度测试报告

| 项 | 内容 |
|----|------|
| 测试对象 | AskFlow 上下文工程（`docs/architecture/context-engineering.md`，L0–L4 + ContextTrace） |
| 对照文档 | `docs/architecture/context-engineering.md` §3/§4/§6/§7/§9；PRD §4.2/§4.3.3/§4.10 |
| 测试日期 | 2026-10-04 |
| 代码基线 | 工作区当前 HEAD（含未提交文件） |
| 执行环境 | `apps/api/.venv`，Python 3.14，本地 `apps/api/.env`（真实 LLM/Embedding） |
| 复现入口 | `evals/probes/context_probe.py`；`pytest`；`evals/runners/run_eval.py` |

---

## 0. 结论摘要

**总体：基础骨架可用，但「诚实 RAG」与「可运营 Prompt」两条核心承诺尚未达成，ContextTrace 与文档不符。**

| 层 | 能力 | 结论 |
|----|------|------|
| L0 安全 | 空/超长/注入拦截、transferred 不进 AI | ✅ 达标 |
| L1 运营 Prompt | 热更新接入生成链路 | ❌ 未接入（仅 Admin CRUD） |
| L2 历史 | 条数/字符预算、staff 镜像、非法 role 丢弃、中段摘要 | ⚠️ 大体达标，system 泄漏 + 旋钮不符 |
| L3 证据 | 弱证据拒答、不调 LLM、证据预算 | ❌ 真实向量模型下拒答失效 |
| L4 当前问题 | 指代消解 | ❌ 未实现（history 被忽略） |
| L5 工具/槽位 | 缺槽/续跑/弃槽 | ✅ 达标 |
| Trace | 结构化 ContextTrace + 落库 | ❌ 仅 3 个字段，未持久化 |

实测数字：

| 测试集 | 结果 |
|--------|------|
| 单元测试（`tests/unit`） | **304 passed / 4 failed** |
| 集成测试（`tests/integration`） | **50 passed / 0 failed** |
| 上下文定向探针（`evals/probes/context_probe.py`） | **14 passed / 5 failed** |
| 离线 eval（仓库根、无 `.env`，纯 BM25） | **8 / 8 ok** |
| 离线 eval（`apps/api` 进程内，启用真实 Embedding） | **7 / 8**，weak_evidence 失败 |

---

## 1. 测试方法

1. **代码走查**：逐项对照 `context-engineering.md` 的旋钮/裁剪算法/trace 字段与实现。
2. **定向探针**：`evals/probes/context_probe.py`（19 项断言），覆盖 L0–L5 与配置对齐。
3. **既有测试**：跑上下文相关单测/集成测试，记录真实通过率。
4. **端到端 eval**：`run_eval.py` 跑 golden + 三类 refusal 语料。
5. **交叉验证**：分别在有/无 `.env`（是否启用真实 Embedding）、不同 CWD 下复跑，排查测试非确定性。

---

## 2. 逐项验收

### L0 安全层 — ✅ 达标

| 验证点 | 结果 | 证据 |
|--------|------|------|
| 空问题拦截 | PASS | `test_harness.py::test_empty_blocked` |
| 超长（>2000）拦截 | PASS | `test_harness.py::test_too_long_blocked` |
| 中英文注入拦截 | PASS | `test_harness.py` 2 例；eval injection 2/2 |
| transferred 不进 AI | PASS | 探针：`flags=['transferred_skip_ai']`，返回固定话术 |
| 输出为空/超长兜底 | PASS | `Harness.finalize` |

### L1 运营 Prompt — ❌ 未接入生成链路（高）

- `PromptService.get_active_content()` 只在 **Admin 读取路由**被调用，生成链路无消费方。
- `ContextAssembler.assemble()` 使用**硬编码 system prompt**（`assembler.py:32-35`），不读取 `rag.system`。
- `app/services/prompt/renderer/`、`versions/`、`cache/` 仅有 `.gitkeep`（空目录）。
- `rag.context` / `clarify.default` 模板未被使用；澄清走 `Harness.MSG_CLARIFY` 常量。
- 「RAG 证据块」由 `assembler.py` 直接拼字符串，而非 `rag.context` 模板。

> 结论：Admin 改话术对线上**无任何效果**；`context-engineering.md` §9 验收 #5、PRD G6「Prompt 热更新」不成立。

### L2 历史层 — ⚠️ 大体达标，两处偏差

✅ 探针通过：
- 条数上限 `max_history_messages=20` → `history_truncated`
- 字符预算 `max_history_chars=6000` → `history_char_budget`
- `staff → assistant` 镜像 → `staff_mirrored`
- 非法 role（如 `tool`）丢弃 → `dropped_illegal_role`
- 中段摘要（E26，threshold 12 / keep 4）→ `history_summarized` + metric

❌ 偏差：
1. **system 消息泄漏进历史**：`policy.py:192` 允许 `{"user","assistant","system"}`，探针显示 `SECRET POLICY` system 历史被保留。文档 §3.2 明确「仅 user/assistant（含 staff 镜像）」「MVP 不把 system 塞进多轮历史」。
2. **旋钮名不符 / 单条截断硬编码**：文档 `CONTEXT_MAX_TURNS`/`CONTEXT_MAX_CHARS_PER_MSG`/`CONTEXT_MAX_TOTAL_CHARS` 在 `config.py` 中不存在，实际复用 `max_history_*`；单条截断写死 `2000`（`policy.py:195`），文档建议 1200 且可配置。

### L3 证据层 — ❌ 真实向量模型下拒答失效（高）

✅ 通过：
- 零命中 → `zero_hit` 拒答，**不调用 LLM**（探针 mock 计数 = 0）。
- 合成低分（0.10）→ `weak_evidence` 拒答；合成高分（0.80）→ 放行。
- 检索缓存 E25 第二次命中（`test_wave_f...`）。

❌ **核心缺陷**：
- 真实 bge-m3 下，**完全无关**的查询「今天月球天气如何量子纠缠」对 4 篇企业 FAQ 的余弦分达 **0.38**，高于 `grounding_threshold=0.35`（`config.py:105`），判定 `pass_through=True` 并**真实调用 LLM** 生成。
- 证据：
  - `tests/unit/test_rewrite_and_rag.py::test_rag_refuse_unrelated` 在本机（`.env` 生效）**单跑连续 3 次失败**，`conf=0.3805 → refused=False`。
  - 全量单测中 `test_out_of_scope_eval::test_eval_runner_passes_corpora` 失败：`weak_evidence → refused=False`。
  - 隔离脚本：`apps/api` CWD（有 `.env`）→ `score=0.3805 pass_through=True`；仓库根（无 `.env`，无 Embedding）→ `score=0.1955 refused=True`。
- 根因：`fuse_hits` 取各通道 **max 原始分**（`rrf.py:37-38,56`），BM25 分（经 `soft+coverage` 归一到 0–1）与向量余弦分**不可比、未校准**，向量通道单独即可越过阈值。`grounding_threshold` 对 embedding 模型是拍脑袋常量。

> 影响：PRD §12.1 #3 / G1「有据可引、没把握就拒答」在**真实部署（配置了向量模型）下退化**。

### L4 当前问题 / 查询改写 — ❌ 指代消解未实现（中）

- `QueryRewriter.rewrite(question, history)` 显式 `_ = history`（`rewriter.py:48`），只有 NFKC/空白规范化 + 同义词扩展。
- 探针：`它超过 7 天还能退吗` + 历史含「退货政策」→ `strategy=none`，`rewritten` 原样，未消解「它」。
- 文档 `query-rewrite.md` §1「指代消解」、`context-engineering.md` L4 目标未落地。

### L5 工具 / 槽位 — ✅ 达标

- 订单号抽取，拒绝手机号/日期；`ask → filled → abandon`；达到 `max_slot_turns` 放弃；意图切换清 `pending_slot`。
- `tests/unit/test_slots.py` 8/8 通过；`test_pipeline_phone_complaint_not_tool_after_stuck_slot` 覆盖弃槽后重组。

### ContextTrace — ❌ 严重不符（中）

- `ContextAssembler.assemble` 只产出 `{history_msgs, evidence_count, evidence_chars}`（`assembler.py:50-54`）。
- 文档 §7 要求：`run_id/trace_id/policy_version/history{raw_count,used_count,truncated_msgs,staff_mirrored}/query{original,rewritten,strategy}/retrieval{...}/budget{...}/flags/route/intent` —— 探针显示**缺失 10 个字段**。
- **未持久化**：`ChatTurn._response_meta`（`turn.py`）不含 `context_trace`；`AgentRun` 模型也无对应列；弱证据早返回路径连基础 3 字段都不写。
- 影响：`context-engineering.md` §9 #6、Dashboard/Gap 归因、`docs/STATUS.md` 引用的 trace 抽检均无法验证。

---

## 3. 测试基础设施问题（影响可信度）

| # | 问题 | 影响 |
|---|------|------|
| T1 | **eval/pytest 非 hermetic**：行为取决于 CWD 是否加载 `apps/api/.env`。有 `.env` → 启用真实 Embedding → 弱证据拒答失败；CI 无 `.env` → 纯 BM25 → 通过 | 缺陷被 CI「绿灯」掩盖 |
| T2 | **网络非确定**：单测依赖真实 `api.gemai.cc`/`api.mmkg.cloud`。本次 `test_retrieval_cache_second_hit_flag` 因 `ConnectError` 失败，日志出现 `429 Too Many Requests` | flaky，无法离线稳定回归 |
| T3 | **全局单例污染**：`test_rag_refuse_unrelated` 整包跑通过、单跑失败，向量/缓存为进程全局 | 结果不可复现 |
| T4 | **覆盖缺口**：无 `history_truncated`/`history_char_budget`/`history_msg_truncated`/`dropped_illegal_role`/harness `history_summarized` 单测；无集成测试验证「staff 回流后 AI 可见」「transferred 无 token 帧」 | 验收 #1/#2/#4 无测试守护 |
| T5 | `pytest` CLI 采集失败（`tests` 非包、缺 editable install）→ 需 `python -m pytest` | 本地/CI 行为差异 |

> 全量单测 4 个失败中，与上下文相关 2 个：`test_out_of_scope_eval`（真实缺陷）、`test_retrieval_cache_second_hit_flag`（网络）；另 2 个为前端结构测试（无关）。

---

## 4. 缺陷清单（按优先级）

| ID | 严重度 | 缺陷 | 位置 |
|----|--------|------|------|
| C-1 | **高** | 弱证据拒答在真实向量模型下失效（阈值/融合未校准） | `rag/fusion/rrf.py:37-56`、`core/config.py:105` |
| C-2 | **高** | L1 运营 Prompt 未接入生成，热更新无效果 | `rag/context/assembler.py:32`、`prompt/service.py:62` |
| C-3 | 中 | 多轮指代消解未实现（history 被忽略） | `rag/query_rewrite/rewriter.py:48` |
| C-4 | 中 | ContextTrace 字段残缺且未持久化 | `rag/context/assembler.py:50`、`chat/session/turn.py`、`models/agent_run.py` |
| C-5 | 中 | system 消息进入 LLM 历史 | `agent/harness/policy.py:192` |
| C-6 | 中 | 文档旋钮与代码不符；单条截断硬编码 2000 | `core/config.py:108-128`、`policy.py:195` |
| C-7 | 中 | 测试非 hermetic/flaky/覆盖缺口 | `tests/*`、`.env` 加载 |
| C-8 | 低 | 证据块无 chunk 字符上限，chunk 数由 `top_k=5` 决定（文档 `RAG_MAX_CHUNKS=6`） | `rag/context/assembler.py`、`rag/pipeline.py` |

---

## 5. 修复建议

1. **C-1（最高）**：对向量分做可校准映射（如按模型/语料标定分数分布，或对向量通道另设阈值），并在 `fuse_hits` 中保留「通道来源」而非直接取 max；补一条**多模型**回归用例，将阈值纳入 eval 基线。验收：配置真实 embedding 时，`test_rag_refuse_unrelated` 与 `EvalRunner` 均通过。
2. **C-2**：在 `RAGPipeline`/`handle_rag` 中按会话 `metadata.system_prompt_key` 调 `PromptService.get_active_content`，失败回落代码常量；补「热更后新会话生效」双实例集成测试。
3. **C-4**：把 Harness 裁剪统计与 rewrite/retrieval/budget 汇总成结构化 trace，写入 `AgentRun`（或消息 `meta`）并脱敏；弱证据路径也要写。
4. **C-3**：实现基于历史的规则/LLM 指代改写（可用现成 `RewriteResult` 的 `llm` strategy 位）。
5. **C-5/C-6**：`_sanitize_history` 收紧为 `{user, assistant}`；把单条上限、字符上限、`RAG_MAX_CHUNKS` 等提成配置项并与文档对齐（或相反：改文档对齐代码，二者必须一致）。
6. **C-7**：测试注入假 LLM/Embedder；`.env` 不得影响测试；补 L2 各 flag 与 transferred/staff 回流的集成用例。

---

## 6. 复现命令

```bash
# 定向探针（离线，19 项）
apps/api/.venv/bin/python evals/probes/context_probe.py

# 上下文相关单测
cd apps/api
.venv/bin/python -m pytest tests/unit/test_harness.py \
  tests/unit/test_wave_f_cache_summary_dispatch.py \
  tests/unit/test_slots.py tests/unit/test_rewrite_and_rag.py -q

# 全量（注意 CWD 影响 Embedding 是否启用）
.venv/bin/python -m pytest tests/unit -q        # 304 passed / 4 failed
.venv/bin/python -m pytest tests/integration -q # 50 passed

# 离线 eval（仓库根，纯 BM25 → 8/8；进程内启用 Embedding → weak_evidence 失败）
apps/api/.venv/bin/python evals/runners/run_eval.py
```

产物：`evals/probes/context_probe.py`（探针）、本报告。

---

## 7. 附：探针明细

| 断言 | 结果 |
|------|------|
| L2 历史条数上限 | ✅ |
| L2 历史字符预算 | ✅ |
| L2 单条消息截断 + flag | ✅ |
| L2 单条截断可配置（1200） | ❌ 硬编码 2000 |
| L2 staff→assistant 镜像 | ✅ |
| L2 非法 role 丢弃 | ✅ |
| L0/L2 system 不得进历史 | ❌ 泄漏 |
| E26 中段摘要压缩 | ✅ |
| E26 harness `history_summarized` flag | ✅ |
| L4 多轮指代消解 | ❌ history 被忽略 |
| L4 同义词规则改写 | ✅ |
| L3 弱证据拒答（低于阈值） | ✅ |
| L3 强证据放行 | ✅ |
| ContextTrace 完整字段（文档 §7） | ❌ 缺 10 字段 |
| ContextAssembler 基础 trace | ✅ |
| L3 弱/零证据拒答不调用 LLM | ✅ |
| L0/L2 transferred 不进 AI | ✅ |
| 文档旋钮与代码配置对齐 | ❌ 5/5 缺失 |
