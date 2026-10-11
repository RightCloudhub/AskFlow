# 一线反馈驱动的运营体验优化（2026-10）

> 角色流转：坐席职员提建议 → 产品经理拆解定位 → 开发实现 → 测试/运维验收。
> 数据来源：`apps/api/scripts/seed_demo.py` 灌入的演示环境（full profile，离线回答）。

## 一、一线职员反馈（原话整理）

我是售后组坐席，每天主要用「人工接管」「工单中心」「知识缺口」三个页面，加上偶尔看对话台回答质量。

| # | 场景 | 原话 |
|---|------|------|
| F1 | 人工接管 | 「会话那一列是一串 UUID，认领人也是 `122bf44c…`，我根本不知道这是哪个客户、被谁接走了。」 |
| F2 | 人工接管 | 「已经被同事认领的会话，我这里还亮着蓝色『认领』按钮，点了才报错。也看不出客户等了多久。」 |
| F3 | 工单中心 | 「已解决的工单还在显示『已解决』按钮；类型一列是 `after_sales`、`logistics` 这种英文。」 |
| F4 | 工单中心 | 「机器人建的工单标题前面带 `[complaint]`，客户看到也很奇怪。」 |
| F5 | 知识缺口 | 「每条缺口的原因都写 `skipped`，没法判断是知识库没写，还是写了但没检索到。」 |
| F6 | 知识缺口 | 「『账号被锁了怎么办』进了缺口，可知识库『账户与安全』明明写了锁定规则。」 |
| F7 | 对话台 | 「问退款多久到账，回答里两条几乎一样的『3-5 个工作日原路返回』，看着像复读。」 |

## 二、产品拆解与精准定位

| ID | 问题本质 | 根因定位（代码） | 优先级 | 方案 | 验收标准 |
|----|----------|------------------|--------|------|----------|
| P1 ← F5 | **数据错误**：缺口原因恒为 `skipped` | `services/chat/side_effects/gap.py` 读的是 `verification.result`；拒答路径该字段固定为 `skipped`（`rag/pipeline.py`），真实原因在 `refusal_reason` | P0 | 记录 `refusal_reason`（`zero_hit` / `weak_evidence`）；前端映射为「无命中」「证据不足」并给出处理建议 | 新缺口 reason ∈ {zero_hit, weak_evidence}；页面不出现英文原因 |
| P2 ← F6 | **检索召回**：同义词缺失 | `data/samples/query_synonyms.yaml` 无「账号/帐号 → 账户」组 | P1 | 新增 `account` 同义组 | 「账号被锁了怎么办」命中「账户与安全」，不再产生缺口 |
| P3 ← F1 | **可读性**：接管列表只有 ID | `HandoffOut` 只返回 `user_id`/`claimed_by` | P1 | API 增加 `user_name`、`claimed_by_name`（一次批量查询，无 N+1）；前端显示客户名、坐席名，「我」高亮 | 列表不再出现裸 UUID；会话 ID 收进详情 |
| P4 ← F2 | **操作误导**：按钮不随状态变化 | `components/handoff/Inbox` 对所有行渲染同一组按钮 | P1 | queued 显示「认领」；claimed 仅认领人显示「交还 AI」，他人显示「已被认领」；新增「等待时长」列 | 已认领行不再出现可点击的「认领」 |
| P5 ← F3 | **操作误导 + 英文枚举** | `TicketsAdminPage` 按钮恒显示；`TICKET_TYPE_LABELS` 只覆盖来源类型 | P1 | 按状态隐藏无效动作；补齐业务类型与意图标签 | 已解决工单无「已解决」按钮；类型列全中文 |
| P6 ← F4 | **对外文案** | `pipeline/handlers/ticket.py::_ticket_title` 用英文意图前缀 | P2 | 改为中文前缀 `【投诉】`；保持前缀稳定，不影响按标题合并 | 新工单标题无英文意图 |
| P7 ← F7 | **回答质量** | `rag/generator/extractive.py` 未对跨来源近重复句去重 | P2 | 字符二元组重叠系数（交集 ÷ 较小集合）≥ 0.7 视为重复，保留排名更高者 | 退款问题回答中「3-5 个工作日」只出现一次 |

### 不做（本轮范围外）
- 坐席实时消息推送（需 WebSocket 坐席通道，见 `docs/engineering/backend-plan.md`）。
- 历史缺口 reason 回填：旧数据保留 `skipped`，前端显示「未记录原因」。
- 已有英文前缀工单不迁移；新旧前缀不会互相合并（只影响迁移当时仍开放的同题工单）。

## 三、开发实现摘要

| ID | 改动文件 |
|----|----------|
| P1 | `app/services/chat/side_effects/gap.py`、`app/services/knowledge/gap/service.py`（同时移除吞异常的 try/except）、`web/src/pages/admin/GapsPage.tsx`、`web/src/components/admin/labels.ts` |
| P2 | `data/samples/query_synonyms.yaml` |
| P3 | `app/schemas/handoff.py`、`app/api/v1/admin/handoffs/routes.py`、`web/src/api/types.ts` |
| P4 | `web/src/components/handoff/Inbox/index.tsx`、`web/src/pages/admin/HandoffsPage.tsx` |
| P5 | `web/src/pages/admin/TicketsAdminPage.tsx`、`web/src/components/admin/labels.ts` |
| P6 | `app/services/agent/pipeline/handlers/ticket.py` |
| P7 | `app/services/rag/generator/extractive.py` |

## 四、测试与验收

见 [`docs/testing/ops-feedback-test-plan.md`](../testing/ops-feedback-test-plan.md)。
