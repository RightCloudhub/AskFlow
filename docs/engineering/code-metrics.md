# 代码硬性指标（强制要求）

| 项 | 内容 |
|----|------|
| **状态** | **强制** — 新代码与改动代码必须满足；评审可据此打回 |
| **适用范围** | `apps/`、`packages/`、`evals/runners/`、项目脚本（不含 `node_modules` / `.venv` / 生成物） |
| **语言** | Python、TypeScript/TSX、Shell（能度量则度量） |
| **更新日期** | 2026-07-18 |

> 与产品契约（`docs/contracts/`）并列：**行为契约**管「做什么」，**本文件**管「怎么写」。

---

## 1. 指标上限

| 指标 | 上限 | 说明 |
| --- | --- | --- |
| 函数长度 | **≤ 50 行**（不含空行） | 单函数/方法体；不含仅含 docstring 的空实现计法以「可执行与声明行」为准时，仍建议体 ≤ 50 |
| 文件大小 | **≤ 300 行** | 含空行与注释的物理行数；超限须拆文件/模块 |
| 嵌套深度 | **≤ 3 层** | `if` / `for` / `while` / `try` / 理解式等控制结构嵌套；函数定义本身不计第 0 层 |
| 位置参数个数 | **≤ 3** | 超出时使用 **dataclass / TypedDict / Pydantic model / 具名 options 结构体** 封装；`self`/`cls` 不计入 |
| 圈复杂度 | **每函数 ≤ 10** | McCabe 复杂度；超限须拆分支或表驱动 |
| 魔数（魔法数字） | **禁止** | 须提取为**命名常量**（模块级或类级）；允许例外见 §3 |

---

## 2. 合规写法（摘要）

### 2.1 函数过长 / 文件过大

- 按步骤拆私有函数或协作对象（prepare → decide → act → finalize）。
- 按业务域拆文件，与 `docs/prd/STRUCTURE.md` 目录域一致。
- 禁止为「压行数」而把多语句挤成一行或删除必要空行后仍超标硬提交。

### 2.2 嵌套与复杂度

- 优先 **早返回（guard clause）**，避免深嵌套 `if/else`。
- 多分支路由用 **字典/表驱动** 或策略对象，而不是长 `if/elif` 链。
- `try` 只包最小失败点；勿把整段业务塞进一层 `try`。

### 2.3 参数过多

```python
# 禁止：位置参数 > 3
def handle(a, b, c, d, e): ...

# 允许：结构体封装
@dataclass
class HandleRequest:
    a: str
    b: str
    c: int
    d: bool
    e: str | None = None

def handle(req: HandleRequest) -> Result: ...
```

TypeScript 侧优先对象参数：

```ts
function handle(opts: HandleOptions): Result { ... }
```

### 2.4 魔数

```python
# 禁止
if confidence < 0.45: ...

# 允许
INTENT_CLARIFY_THRESHOLD = 0.45
if confidence < INTENT_CLARIFY_THRESHOLD: ...
```

配置项（环境变量 / Settings）也视为命名常量来源；业务代码中勿再写裸字面量重复阈值。

---

## 3. 明确例外（须在评审中可辩护）

| 例外 | 条件 |
|------|------|
| 字面量 `0` / `1` / `-1` / `2` | 作为下标、步长、空集合边界等惯用写法 |
| 字面量 `""` / `[]` / `{}` / `None`/`null` | 空值与默认容器 |
| HTTP 状态码 | 使用标准库或框架常量时优先；裸 `404` 等若出现须靠近路由层且语义明显 |
| 协议/契约固定字段 | 与外部 API 字段名、JSON key 一一对应的字符串（仍禁止无意义数字阈值） |
| 测试数据 | `tests/` / `evals/**/cases.jsonl` 中的用例字面量可放宽魔数；**函数长度与文件大小仍建议遵守**，超大 fixture 外置文件 |
| 生成代码 | 工具生成且标注 `DO NOT EDIT` 的文件可豁免，但不得手改后继续豁免 |

**无例外：** 生产路径上的超时毫秒、重试次数、阈值、预算步数、端口以外的业务数字——必须命名常量或配置。

---

## 4. 存量与增量策略

| 类型 | 要求 |
|------|------|
| **新增文件 / 新函数** | 必须 100% 满足 §1 |
| **修改已有代码** | 所改函数与所触及文件应向合规收敛；禁止在已超标文件上继续堆逻辑 |
| **明显超标热点** | 修改前先拆分到合规，或同一 PR 内完成拆分 |

---

## 5. 检查工具（已提供）

```bash
# 仓库根目录
python3 scripts/ops/check_code_metrics.py
```

| 产出 | 路径 |
|------|------|
| 控制台摘要 | stdout；exit `1` = 存在违规 |
| JSON 明细 | `docs/engineering/code-metrics-report.json` |
| 最近人工审计 | [code-metrics-audit.md](./code-metrics-audit.md) |

| 语言 | 覆盖 |
|------|------|
| Python | 六项指标（AST） |
| TypeScript/TSX | 目前仅 **文件大小**；函数级需后续 ESLint |

可选用增强：`ruff` / `radon` / `eslint` 复杂度规则接入 CI。本地与 CI 门禁落地后以自动化为准；在此之前 **代码评审按本表强制执行**。

---

## 6. 相关文档

| 文档 | 关系 |
|------|------|
| [docs/contracts/agent-behavior.md](../contracts/agent-behavior.md) | Agent 行为契约（冷更新） |
| [docs/prd/STRUCTURE.md](../prd/STRUCTURE.md) | 目录与域拆分，利于控制文件大小 |
| [AGENTS.md](../../AGENTS.md) | 面向助手的工程约定入口 |
