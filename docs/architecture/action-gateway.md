# Action Gateway：单一执行关口与操作台账

更新：2026-10-15。实现 [Optimized Architecture](../../arch.md) §4.4 / §4.11 的结构性变更一：
**所有副作用（旧工具、旧管线副作用、持久任务操作）经过同一策略、幂等、确认与台账关口**，不再存在绕过治理的执行路径。

## 1. 结构

```text
调用方（任务执行器 / 工具桥 / 聊天副作用）
        │  capability + args + ExecContext(scope, assurance, task_id|turn_id)
        ▼
Action Gateway（app/services/agent/gateway/）
  1. capabilities.py  能力目录：副作用等级、身份要求、确认、补偿、成本
  2. policy.py        策略引擎（内置、带版本）：assurance 门槛 + 业务限额
  3. idempotency.py   key = sha256(scope | step | capability | 规范化参数)
  4. confirmation.py  签名确认令牌：绑定参数、单次使用、可过期
  5. ledger.py        只追加台账（哈希链），状态变更=新行
  6. gateway.py       编排：拒绝/待确认/意图→执行→结果
        │
        ▼
下游适配器（域连接器 / 工具 handler / 工单·转交仓储）
```

## 2. 不变量

1. **先写意图再调用**：`INTENT` 行在外部调用前提交；随后追加 `EXECUTED / FAILED / OUTCOME_UNKNOWN`。
2. **结果未知不得盲目重放**：写操作超时记 `OUTCOME_UNKNOWN`；任务侧由检查点门控重放（`reconcile_required`），台账提供查证依据。
3. **拒绝即留痕**：策略拒绝写入 `DENIED` 行（含原因），并抛 `PermissionError("policy_denied")`，不计入任务预算。
4. **确认令牌绑定参数**：`HMAC(scope|step|args_hash|exp|nonce)`；参数变化即失效；nonce 单次消费（条件 UPDATE）。
5. **台账只追加**：状态变化=同 `idempotency_key` 的新行；`prev_hash`/`row_hash` 形成哈希链，最新行即当前状态。
6. **模型只能看到被允许的能力**：能力目录 + 策略是两道防线；`Environment.permissions` 仍由认证代码提供。

## 3. 能力与策略

- 能力等级：`read` / `reversible_write` / `irreversible_write`。
  不可逆能力（`refund.submit`、`orders.cancel`、`payments.refund`）自动要求确认；
  `refund.submit` 另要求 L2 身份，且金额超过 50 欧元需人工审批（`amount_cents` 按分换算）。
- 策略引擎为内置注册表（`GATEWAY_POLICY_VERSION` 版本化），每次评估随台账留档；后续可替换为 OPA/Cedar。
- 旧管线副作用以 `spec_for_side_effect` 注册（`ticket.create`、`handoff.enqueue` 等，reversible，L1）；
  旧工具以 `spec_for_tool` 注册（read，L1），每次调用写 `INTENT → EXECUTED/FAILED` 台账行。

## 4. 执行方接入

| 路径 | 接入点 | 说明 |
|---|---|---|
| 持久任务操作 | `service/executor.py` + `executor_parks.py` | 策略/确认/审批/台账；VERIFIED 由 runtime 在目标验证通过后标记 |
| 旧工具 | `gateway/tool_bridge.py`（`handle_tool` 构建） | 每尝试一对 INTENT/结果行，拒绝返回 `error_class=auth` |
| 工单/转交副作用 | `chat/side_effects/{ticket,handoff}.py` | 与回合同事务写台账；拒绝标记 `denied` |
| 退款域 | `domains/refund.py`（既有） | 不可逆：L2 + 确认 + 超限人工审批（`owner_review:human_approval`） |

确认流程：执行器在需要确认时签发令牌 → 任务进入 `waiting_customer`（`wake_condition=confirm:<nonce>`）
→ 用户在聊天回复「确认」（Turn Router 校验并消费 nonce）→ 任务激活，`Task.confirmations` 授予匹配
（能力+参数哈希）→ 执行器放行；成功后授权被消费。outbox 事件 `confirmation.requested` 同步推送提示。

## 5. 台账与查询

表 `operation_ledger`（迁移 `20261015_governance_tables`）：`op_id, seq, organization_id, customer_id,
task_id|turn_id, step, capability, capability_version, args_hash, idempotency_key, policy_decision,
policy_version, actor, status, external_ref, error, latency_ms, cost, prev_hash, row_hash, created_at`。
状态集合：`INTENT / EXECUTED / FAILED / OUTCOME_UNKNOWN / VERIFIED / COMPENSATED / DENIED / NEEDS_CONFIRMATION`。
当前状态 = 同 `idempotency_key` 的最新 `seq` 行；`record_verified` 在目标验证通过后把 `EXECUTED` 写操作标记 `VERIFIED`；`record_compensated` 把已执行的写操作标记 `COMPENSATED`。

## 6. 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `GATEWAY_POLICY_VERSION` | `1` | 策略版本，写入台账与决策 |
| `CONFIRMATION_TTL_SECONDS` | `86400` | 确认令牌有效期 |
| `OTP_TTL_SECONDS` / `OTP_MAX_ATTEMPTS` | `300` / `5` | 步进验证码有效期与尝试上限 |
| `ASSURANCE_TTL_SECONDS` | `1800` | 提升后身份的会话有效期 |

## 7. 边界

- 补偿执行器（2026-10-16）：`Operation.compensation` 为普通 op id 时按原参数执行一次并把原操作标记 `COMPENSATED`（仅 `EXECUTED`/`OUTCOME_UNKNOWN` 可迁移，预算豁免）；`irreversible:`/`owner_review:` 前缀、未知写入或有未知写操作在途时转 `owner_review:no_safe_compensation`，补偿失败转 `owner_review:compensation_failed`。
- 业务限额目前仅内置退款金额一条；未提供运营配置界面。
- 台账为应用层只追加（无 UPDATE/DELETE 路径）；生产库可另行 `REVOKE UPDATE, DELETE`。
- 单租户部署：`organization_id` 固定 `deployment`，未实现行级安全。

测试：`tests/unit/test_gateway.py`（策略/幂等/令牌/台账/桥）、`tests/unit/test_domains_refund.py`（L2+确认+超限）、
`tests/unit/test_service_agent.py`、`tests/unit/test_service_recovery.py`、`tests/unit/test_compensation.py`（补偿执行与台账标记）。
