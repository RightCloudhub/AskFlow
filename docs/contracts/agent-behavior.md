# Agent 行为契约

> PRD v1.1 §1.5 原则 6 / 10：代码即契约；自研 Loop 为行为真相。本文描述**实现必须遵守**的产品语义；  
> 变更路由集 / 意图集 / Harness 硬规则 / Loop 节点 = 契约冷更新（改代码 + 本文 + 测试），不可仅靠运营配置完成。

机器可读骨架：`packages/contracts/agent/`。  
完整产品语义：`docs/prd/PRD.md` §3.5、§4.13–4.18。

---

## 1. 合法集合（冷）

| 集合 | 值 |
|------|-----|
| Intents (MVP) | `faq`, `product`, `order_query`, `fault_report`, `complaint`, `handoff` |
| Routes | `rag`, `tool`, `ticket`, `handoff`, `clarify` |
| Loop phases | `plan`, `act`, `observe`, `recover`, `finalize` |
| LLM purposes | `intent_classify`, `query_rewrite`, `rag_generate`, `handoff_summary`, `gap_draft_assist`, `embedding`（可扩展须文档化） |
| ConversationStatus | `active`, `transferred`, `closed` |
| MessageRole（LLM 历史） | `user`, `assistant`（staff 须镜像） |

新增 intent/route/purpose/tool 必须：注册 → 路由表 → 测试 → 更新本文与 PRD。

---

## 2. Harness 硬规则（不可进 Prompt 模板表）

| 阶段 | 规则 |
|------|------|
| prepare | 空 / 超长 / 注入 → 停止 + **代码常量**文案 |
| choose_route | 非白名单 route → `rag`；过低置信 → `clarify` |
| finalize | 空输出 → 兜底；超长 → 截断 + 提示 |
| transferred | **禁止**调用 AI 流水线 |

---

## 3. 路由默认表（内置兜底）

| Intent | Route |
|--------|-------|
| faq | rag |
| product | rag |
| order_query | tool |
| fault_report | ticket |
| complaint | ticket |
| handoff | handoff |

运营映射可覆盖，但 target 必须 ∈ 合法 Routes。

---

## 4. Honest RAG

1. grounding 失败 → **不调 LLM**  
2. 答案引用 `[n]` 必须能映射 `sources[]`  
3. 置信度随 `message_end` 下发  
4. 查询改写不得为提高命中率而把无依据问题改成「假相关」查询（评测红线）  

---

## 5. 工具与槽位

1. 工具 handler **仅** Registry 可执行；模型不可越权  
2. webhook 密钥走配置  
3. 失败可 mock，且 `data_source` 标明  
4. metadata 槽位 merge-patch  
5. 最大追问轮次（建议 3）后 clarify  
6. 失败类分流：超时可重试；参数错不盲重试；4xx/权限不重试  

## 5.1 Multi-step Loop 硬预算

| 项 | 默认 | 超限 |
|----|------|------|
| MAX_STEPS | 6 | clarify 或 handoff |
| MAX_TOOL_CALLS | 4 | 同上 |
| MAX_WALL_MS | 45000 | 取消 + 降级话术 |
| MAX_RETRIES_PER_TOOL | 2 | 按 error_class |

禁止：无限自主 Agent；以托管 Assistants 线程替代自研 Loop 作为真相来源。

## 5.2 多模型

1. 每次 LLM 调用必须带 `purpose`  
2. primary 失败走 fallback 链，耗尽则确定性回落  
3. 禁止无理由默认最贵旗舰模型  
4. token 与估算费用 best-effort 入 Cost Ledger  

---

## 6. Ticket / Handoff

1. 工单创建唯一仓储入口  
2. open 单 (user_id, title) 逻辑唯一  
3. 一会话至多一个 open handoff  
4. claim 冲突 409  
5. 摘要失败不阻塞入队  
6. 超时 → 高优工单 + 会话回 active  

---

## 7. 可观测契约

每次 run 至少具备：

- `run_id`, `trace_id`, `route`, `intent`  
- `flags[]`, `policy_version`  
- rag 时：`rewrite.strategy`, `grounding_score` 或 refusal reason  

失败写 trace 不得反压用户消息主路径。

---

## 8. 配置热 vs 冷

| 热更新 | 冷更新 |
|--------|--------|
| intent→route 映射值 | 新增 intent / route 枚举 |
| Prompt 模板正文与 active 版本 | Harness 文案与阈值 |
| 同义改写词典（文件/配置） | 工具 handler 签名 |
| 部分 grounding 阈值（须 eval） | WS 协议 type 集合 |

## 9. 持久服务任务增量契约（2026-10-04）

适用于 `services/agent/intake/`、`service/`、`domains/`、`memory/` 及 `workers/service_tasks.py`。旧消息路由契约继续适用；任务目标不等同于路由名。实现边界见 [运行时](../architecture/customer-service-runtime.md) 与 [差距清单](../architecture/agent-conformance.md)。

| 边界 | 当前契约 |
|---|---|
| 默认接管 | `SERVICE_TASKS_GOALS=order_status`；工单/人工转交需白名单，退款/通知不在默认策略注册表 |
| 认证与权限 | Scope 来自可信应用；历史、摘要、记忆、任务输入和模型候选不能授予权限 |
| 创建与执行 | 聊天消息/任务/派发同事务；操作意图与累计消耗先持久化，后调用业务系统 |
| 并发 | 任务版本 CAS；派发租约；worker 为带订单号的任务取得范围内对象租约 |
| 结果未知 | 外部写入超时或回执异常记 unknown；不得盲目重放，需原请求键查证或责任人处理 |
| 预算 | 任务调用与无进展次数有默认上限；费用与 deadline 可选，续跑不清零；费用依赖宿主估计 |
| 完成 | 应用 verify 裁定；模拟/过期证据不结案，订单需客户/订单匹配；工单目前只验证登记成功 |
| 取消与接管 | 控制动作增加版本，不代表已发出的业务操作撤销；保留未决台账 |
| 人工接管 | 当前人员必须已领取同客户/同会话的 handoff；handed_off 不表示原问题解决 |
| 记忆 | 当前选择与实时事实优先；过期/删除项不读取；权限和对象归属不从记忆恢复 |
| 历史摘要 | 以 user 角色及历史数据标记进入上下文，不提升为系统指令 |
| 结果交付 | 仅向匹配客户的 active 会话按任务版本去重写入；无后台 WS 广播保证 |

TaskStatus：`active`、`waiting_customer`、`waiting_external`、`handed_off`、`resolved`、`closed_unresolved`。自动调度仅推进 active 和到期 `retry:*`；`VerifiedWakeup` 不能替代外部事件验签。`Operation.compensation` 为声明字段：普通 op id 由补偿执行器自动执行并标记 `COMPENSATED`（2026-10-16）；`irreversible:`/`owner_review:` 前缀与未知写入转人工。

## 10. 统一执行与路由契约（2026-10-15，arch.md 实施）

适用于 `services/agent/gateway/`、`services/agent/router/`、`services/chat/side_effects/`、`services/channels/`、`services/outbox/`。实现说明见 [Action Gateway](../architecture/action-gateway.md)。

| 边界 | 当前契约 |
|---|---|
| Turn Router | 每回合按固定优先级：待验证码 → 控制意图 → 在办任务确认/续办 → 相关修改 → 无关直答+提醒 → 新意图；每条路由写 `router_decisions` |
| RouterDecision.route | `CONTROL` / `TASK_RESUME` / `TASK_CREATE` / `CLARIFY` / `STEP_UP` / `INTERACTIVE` / `REFUSE` / `HANDOFF`（受理层集合；消息流水线旧 Route 集合不变） |
| 控制意图 | 仅在会话存在在办任务时生效；取消仅针对可控制状态（active/waiting_*）；已转交/已结束拒绝 |
| 身份等级 | L0 匿名（Widget 访客）/ L1 渠道已验证 / L2 已登录或步进验证；目标可声明 `required_assurance`，不足时进入验证码步进流程 |
| Action Gateway | 所有副作用先策略后调用；拒绝写 `DENIED` 且不消耗任务预算；不可逆写需确认令牌或人工审批 |
| 操作台账 | 只追加、哈希链；写意图先于外部调用；`OUTCOME_UNKNOWN` 不得盲目重放 |
| 确认流 | 令牌绑定参数、单次使用、可过期；聊天回复「确认」消费 nonce 并授予 `ConfirmationGrant`；重放被拒 |
| Outbox / Inbox | 状态变更与事件同事务；inbox 以 `(channel, message_id)` 去重且按会话有序；重放 webhook 只产生一次回合 |
| 输出护栏 | `Harness.finalize` 统一执行：承诺性语句剥离、提示词泄漏抹除、长度截断 |
| 不可信文本 | 检索证据以 «SOURCE» 定界并剥离指令行；工具输出字段经同样清洗后进入答复 |

冷更新（改代码 + 本文 + 测试）：新增 router route、能力等级、策略字段、护栏模式。
