# AskFlow — Agent / 贡献者工程约定

本文件约束在本仓库内编写或修改代码的助手与人类贡献者。

## 强制：代码硬性指标

**完整条文：** [docs/engineering/code-metrics.md](./docs/engineering/code-metrics.md)

| 指标 | 上限 |
| --- | --- |
| 函数长度 | ≤ 50 行（不含空行） |
| 文件大小 | ≤ 300 行 |
| 嵌套深度 | ≤ 3 层 |
| 位置参数个数 | ≤ 3（超出时使用结构体封装） |
| 圈复杂度 | 每函数 ≤ 10 |
| 魔数（魔法数字） | 禁止；须提取为命名常量 |

新增与改动代码必须满足上表；修改已超标文件时须先拆分或同 PR 收敛。例外仅见 `docs/engineering/code-metrics.md` §3。

## 产品与架构（摘要）

- 产品需求：`docs/prd/PRD.md`
- 完成状态：`docs/STATUS.md`
- 目录映射：`docs/prd/STRUCTURE.md`
- Agent 行为契约：`docs/contracts/agent-behavior.md`
- 三大支柱：`docs/architecture/pillars.md`
