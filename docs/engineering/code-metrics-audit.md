# 代码硬性指标审计报告

| 项 | 内容 |
|----|------|
| **依据** | [code-metrics.md](./code-metrics.md) |
| **工具** | `scripts/ops/check_code_metrics.py` |
| **机器可读** | [code-metrics-report.json](./code-metrics-report.json) |
| **审计日期** | 2026-07-18 |
| **结论** | **FAIL** — 全库未达标；生产结构项有明确热点 |

---

## 1. 扫描范围与方法

| 项 | 值 |
|----|-----|
| 范围 | `apps/`、`packages/`、`evals/runners/`、`scripts/` |
| 排除 | `node_modules`、`.venv`、`dist`、`__pycache__` |
| 文件数 | **218**（Python 195 · TS/TSX 23） |
| Python | AST：函数长度 / 嵌套 / 参数 / 圈复杂度 / 魔数 |
| TS/TSX | **仅**文件行数（无本地 ESLint AST） |

**魔数例外（与规范 §3 一致）：** `0/1/-1/2`、模块/类级赋值、类型注解；HTTP 状态码仍计违规（规范写「优先框架常量」）。

---

## 2. 总览

| 指标 | 上限 | 违规数 | 其中 api 生产 | tests | scripts |
|------|------|------:|-------------:|------:|--------:|
| 文件大小 | ≤ 300 行 | **2** | 1 | 0 | 1 |
| 函数长度 | ≤ 50 行（非空） | **16** | 12 | 2 | 2 |
| 嵌套深度 | ≤ 3 | **10** | 8 | 1 | 1 |
| 位置参数 | ≤ 3 | **18** | 18 | 0 | 0 |
| 圈复杂度 | ≤ 10 | **25** | 14 | 9 | 2 |
| 魔数 | 禁止 | **191** | 102 | 82 | 7 |
| **合计** | | **262** | **155** | **94** | **13** |

> 测试中魔数/复杂度按规范可**放宽魔数**，但函数长度与文件大小仍建议遵守。  
> **生产结构违规（不含魔数）：53 条** — 整改优先看这部分。

**TS/TSX：** 23 个源文件均 ≤300 行，无 `file_size` 违规；函数级指标未检。

---

## 3. 生产代码 P0 热点（优先拆）

### 3.1 文件过大

| 文件 | 行数 | 动作 |
|------|-----:|------|
| `apps/api/app/services/agent/pipeline/runner.py` | **341** | 按 route 拆 handler 文件（rag/tool/ticket/handoff） |

接近上限（预警）：`chat/routes.py` 253、`chat/session/service.py` 222、`harness/policy.py` 212。

### 3.2 函数过长（生产 Top）

| 位置 | 非空行 | 建议 |
|------|------:|------|
| `pipeline/runner.py` `handle()` | **220** | 表驱动 route 分发 + 每路由一函数 |
| `chat/session/service.py` `handle_user_message()` | **122** | 侧效应/工单/转接拆私有步骤 |
| `chat/routes.py` `chat_ws()` | **101** | 鉴权 / 收消息 / 推流 三段 |
| `agent/loop/engine.py` `run()` | **98** | plan/act/recover 分函数 |
| `eval_runner/runner.py` `run()` | **76** | case 执行与汇总分离 |
| `knowledge/indexer/service.py` `index_document()` | **72** | 读→切→嵌→写 管道 |
| `connectors/service.py` `invoke()` | **68** | 请求/重试/降级 分离 |
| `handoff/timeout.py` `sweep()` | **62** | 扫描与单条处理分离 |
| 其余 4 个 | 51–53 | 小幅抽函数即可 |

### 3.3 圈复杂度（生产 Top，limit 10）

| 函数 | CC | 备注 |
|------|---:|------|
| `handle_user_message` | **31** | 全局最高 |
| `eval_runner.run` | **29** | |
| `chat_ws` | **24** | |
| `MessagePipeline.handle` | **19** | 与文件/函数超标重叠 |
| `connectors.invoke` | **17** | |
| `query_rewrite.rewrite` | **16** | |
| 另 8 个 | 11–14 | 含 oidc / handoff queue / intent |

### 3.4 嵌套深度（生产）

| 函数 | 深度 |
|------|-----:|
| `chat_ws` / `emit_safe` | **5** |
| `choose_route` / `classify` / `loop.run` / `handle_user_message` / `load_jsonl_cases` / `rewrite` | **4** |

### 3.5 位置参数 > 3

**18 处几乎全是 FastAPI 路由**（`db` + `user` + path + body）。框架惯用 `Depends` 注入，机械数参数会超标。

**整改建议（二选一，需产品/规范拍板）：**

1. **规范补充例外：** FastAPI/Starlette 路由处理函数的依赖注入参数不计入位置参数；或  
2. **工程收敛：** path/body 收入单一 request model，仅保留 `db`/`user`/`payload` ≤3。

当前脚本按字面强制计 18 条违规。

---

## 4. 魔数（191）

| 来源 | 约数 | 说明 |
|------|-----:|------|
| api 生产 | 102 | 阈值、超时、截断长度、HTTP 码、分页 limit 等 |
| tests | 82 | 规范允许放宽；可后置 |
| scripts | 7 | 含检查脚本自身 |

生产常见裸字面量：`404`/`409`/`503`、`500`/`2000`/`1000`、WS `4400`/`4401`、`0.45` 类阈值若未走 Settings 等。

**建议：** 集中 `app/core/constants.py` 或域内 `constants.py`，HTTP 用 `starlette.status`。

---

## 5. 达标率粗估

| 视角 | 估计 |
|------|------|
| 全库「零违规」 | **未达标**（262） |
| 生产「结构四项」文件/函数/嵌套/复杂度 | 约 **十数个核心函数** 拖垮，非全面腐烂 |
| 文件行数 | **1/195** 生产 py 超标（+检查脚本自身） |
| 前端 TS | 文件行数 **全过**；函数级 **未测** |

---

## 6. 建议整改批次（工程量粗估）

| 批次 | 范围 | 人日 | 预期 |
|:----:|------|-----:|------|
| B1 | 拆 `pipeline/runner.py` + `handle()` | 1–2 | 消 file_size + 最大函数/CC |
| B2 | `handle_user_message` + `chat_ws` + `loop.run` | 2–3 | 消 Top CC/长度/嵌套 |
| B3 | indexer / connector / handoff timeout / rag.run / notify | 2–3 | 其余函数长度 |
| B4 | 魔数 → 常量 / status 模块 | 1–2 | 生产 magic 清零 |
| B5 | 路由参数策略（规范例外或 request model） | 0.5–2 | 参数项清零 |
| B6 | 测试超标函数（可选） | 1–2 | 测试也合规 |
| **合计** | | **~8–14** | 生产结构 + 魔数基本绿 |

---

## 7. 复跑命令

```bash
python3 scripts/ops/check_code_metrics.py
# exit 0 = PASS；报告写入 docs/engineering/code-metrics-report.json
```

---

## 8. 检查器自指说明

`scripts/ops/check_code_metrics.py` 本身 **563 行**，违反 file_size / 部分函数指标。后续可拆 `metrics_ast.py` + `metrics_report.py`，或将 `scripts/ops` 列为工具豁免（若采纳须写回 code-metrics.md §3）。
