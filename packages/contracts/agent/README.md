# Agent Contracts Package

行为契约的**可版本化**放置处。权威语义说明见：

- `docs/contracts/agent-behavior.md`
- `docs/prd/PRD.md` §4.3–4.7

## 建议文件（实现阶段补齐）

```
agent/
├── intents.yaml          # 合法意图与默认 route
├── routes.yaml           # 合法路由集
├── harness_policy.yaml   # 阈值与 flag 名（非运营文案全文可放代码）
├── tools.yaml            # 工具名与入参 schema
└── README.md
```

CI 可校验：代码中的 Enum ⊆ yaml 集合。
