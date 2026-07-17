# Agent 消息处理流水线

> 对应 PRD v1.1 §3.2、§3.5、§4.3–4.7、**§4.13 Multi-step Loop**、§4.14 Model Router。  
> 代码：`apps/api/app/services/agent/pipeline/`、`loop/`、`model_router/`（规划中）。

---

## 1. 总览

```
WS message
  → 鉴权 / 限流
  → 会话状态？
       transferred → 仅落库 + 通知坐席（不调 AI）
       active      → Agent 流水线
  → 用户消息落库
  → Harness.prepare
  → 槽位续跑判定
  → 意图分类（ModelRouter purpose=intent_classify）
  → 路由（运营配置 → 内置 → 合法集）
  → Harness.choose_route
  → 分支：rag | tool(Loop) | ticket | handoff | clarify
  → Harness 输出约束
  → CostLedger 记账
  → 助手消息落库
  → 知识缺口雷达（best-effort）
  → WS：token* · source · intent · ticket/handoff · message_end
```

合法路由集：`{rag, ticket, handoff, clarify, tool}`。

### Multi-step Loop（tool 路径，PRD §4.13）

```
PLAN → ACT → OBSERVE → RECOVER ↺（未完成且未超预算）→ FINALIZE
```

硬预算：`MAX_STEPS=6` · `MAX_TOOL_CALLS=4` · `MAX_WALL_MS=45s`。详见 PRD。

---

## 2. 阶段详解

### 2.1 Harness.prepare

| 条件 | 动作 |
|------|------|
| 空问题 | 停止 + 固定话术 |
| 超长（如 &gt;2000 字） | 停止 |
| Prompt 注入 / 控制类 | 停止（安全文案不可运营改） |
| 历史过长 / 单条过长 | 裁剪 + flag |
| 非法 role | 丢弃；staff 镜像为 assistant |

### 2.2 槽位续跑

见 PRD §4.4.2：命中参数 → 跳过分类高置信 tool；异意图高置信 → 弃槽。

### 2.3 意图（MVP 6 类）

`faq` · `product` · `order_query` · `fault_report` · `complaint` · `handoff`

策略：规则 → LLM JSON 比高；过低 clarify；失败回落 faq/规则。  
`handoff` 须共现，禁止仅 “agent” 误触发。

### 2.4 路由顺序

```
1. 无 intent → rag
2. 需澄清且低置信 → clarify
3. 运营 intent→route 映射（热更）
4. 内置兜底表
5. 非法 target → rag + 告警
6. Harness：白名单 / 低置信 → clarify 或 rag
```

### 2.5 分支副作用

| route | 副作用 |
|-------|--------|
| rag | 改写→检索→生成或拒答 |
| tool | 执行工具 / 追问槽位 |
| ticket | 统一仓储建单（去重红线） |
| handoff | 摘要(硬超时) + 入队 + transferred |
| clarify | 澄清话术 |

### 2.6 finalize

空输出兜底；超长截断；写 trace；gap 信号 best-effort。

---

## 3. 与上下文 / 改写 / 监控的接合点

| 阶段 | 文档 |
|------|------|
| 历史与证据组装 | [context-engineering.md](./context-engineering.md) |
| rag 分支检索 query | [query-rewrite.md](./query-rewrite.md) |
| 全阶段埋点 | [../observability/monitoring.md](../observability/monitoring.md) |
| run_id / spans | [../observability/tracing.md](../observability/tracing.md) |

---

## 4. 并发与一致性红线

| 红线 | 机制 |
|------|------|
| 开放工单 user+title 唯一 | partial unique + 收敛 |
| 一会话一 open handoff | partial unique + 409 claim |
| 工单禁止旁路 insert | 唯一 repository 入口 |
| 配置缓存 epoch | 加载中 invalidate 丢弃 |
| metadata | merge-patch only |

---

## 5. 测试矩阵（摘要）

| 路径 | 类型 |
|------|------|
| FAQ 幸福路径 | 集成 |
| 弱检索拒答 | eval + 单测 |
| 订单槽位 3 轮 | 手工/集成 |
| handoff 409 / 超时 | 集成 |
| transferred 不进 AI | 集成 |
| 注入拦截 | 单测 |
