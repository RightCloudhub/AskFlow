# 业务闭环 · 安全审查 · 兜底评估

| 项 | 内容 |
|----|------|
| **日期** | 2026-07-18 |
| **范围** | 试点 MULTI-CHANNEL 代码态（PRD v1.3 / STATUS） |
| **结论** | **试点可用（有条件）**：主业务环代码闭环；安全 L1–L6 基本到位，限流与后台扫描已补；GA 仍需 IdP/渗透/合同取证 |

---

## 1. 业务闭环

| 环 | 链路 | 状态 | 缺口 / 备注 |
|----|------|:----:|-------------|
| **问答** | 登录/访客 → Harness → 意图 → RAG/tool → 回复 + sources | ✅ | 弱证据拒答不调生成 |
| **工具订单** | 槽位补号 → search_order → webhook / **mock** | ✅ | `data_source` 标明 mock |
| **工单** | ticket 路由 → create_or_get_open → 可选 notify | ✅ | 去重并发 |
| **暖转人工** | handoff enqueue → claim CAS → return AI | ✅ | 队列技能组过滤 |
| **转人工超时** | queued 超时 → 高优工单 + 会话回 active + notify | ✅ | **后台周期任务已接入** `enterprise_jobs`；亦可 Admin 触发 |
| **SLA** | 分级扫描 warning/breached → notify | ✅ | Admin 手动 scan + **后台周期** |
| **知识回流** | refuse(弱证据) → Gap → Draft 审核 → index | ✅ | OOS refuse 不记 gap（正确） |
| **反馈** | 👍/👎 → Feedback | ✅ | 进 QC 汇总 |
| **成本 / Run** | ledger 落库 → costs / agent-runs 回放 | ✅ | side-effect best-effort |
| **SSO** | OIDC mock(dev) / JWKS(prod) → JIT | ✅ | 生产需关 mock |
| **Widget** | session → 同流水线 → 隔离 | ✅ | visitor 身份 sha256 |
| **飞书** | events → 同流水线 → 可选回复 API | ✅ | 生产 fail-closed token |
| **质检** | summary / low-quality score | ✅ 骨架 | 无二次 LLM 质检 |
| **Launch Card** | 变更预期 → measure 回填 | ✅ | 运营流程依赖 |

### 闭环依赖运维的部分

1. 配置 `NOTIFY_WEBHOOK_URL`，否则通知仅 sink/DB log  
2. `SWEEPER_ENABLED=1`（默认）且非 test；多副本下 CAS 安全但**每个进程都会跑扫描**（可接受；亦可外部 cron 调 `/admin/system/enterprise-jobs/run` 并关进程内 sweeper）  
3. 连接器 / 订单 URL 指向真实内网  
4. 飞书 App 凭证（仅出站回复需要）

---

## 2. 安全审查（对照 `security-and-fallback.md`）

### L1 入口

| 控制 | 状态 |
|------|:----:|
| JWT Bearer REST | ✅ |
| WS 首帧 auth（禁止 query token） | ✅ |
| 角色 require_admin / agent | ✅ |
| 生产弱 SECRET 拒启 | ✅ |
| CORS 白名单 | ✅（需正确配 `CORS_ORIGINS`） |
| **IP 限流** | ✅ 新增 in-process（test 跳过；多 worker 非全局精确） |
| `/metrics` 无鉴权 | ⚠️ 可选 `METRICS_TOKEN`（生产 like + 配置时校验 `X-Metrics-Token`）；**仍建议内网** |
| Widget / 飞书 匿名面 | ⚠️ 依赖限流 + Feishu token；无验证码 |

### L2–L3 Harness

| 控制 | 状态 |
|------|:----:|
| 空/超长/注入拦截 | ✅ 代码常量文案 |
| 历史 role 清洗 | ✅ |
| 路由白名单 / 低置信 clarify | ✅ |
| transferred 跳过 AI | ✅ |
| out_of_scope refuse | ✅ |

### L4–L5 执行与输出

| 控制 | 状态 |
|------|:----:|
| 工具 Registry 白名单 | ✅ |
| 订单 mock 降级 + data_source | ✅ |
| 连接器 HTTP 失败 mock | ✅ |
| 模型 fallback 链 | ✅ |
| 空输出 / 截断 finalize | ✅ |
| Grounding 拒答不胡编 | ✅ |

### L6 数据与审计

| 控制 | 状态 |
|------|:----:|
| 密码 bcrypt | ✅ |
| 审计 mask email/token/password keys | ✅ |
| SIEM export | ✅ 骨架 |
| 用户导出/删除 | ✅ |
| 扩展 PII（身份证/银行卡） | ⏳ 未做 |
| 审计防篡改 | ⏳ 未做 |

### 已知残余风险（按优先级）

| P | 项 | 建议 |
|---|-----|------|
| P0 运维 | 生产 `OIDC_MOCK` / `ASKFLOW_ENV=development` 误配 | 发布检查清单硬门禁 |
| P0 运维 | Feishu 未配 `FEISHU_VERIFICATION_TOKEN` | 生产 fail-closed 已实现；必须配 token |
| P1 | 进程内限流非集群精确 | 前置 nginx/redis 限流 |
| P1 | `/metrics` 公网暴露 | 内网 + METRICS_TOKEN |
| P1 | 后台 sweeper 每副本一份 | 或改外部 cron 单点 |
| P2 | 扩展 PII / 审计防篡改 | Wave D E9 余量 |
| P2 | 企微/钉钉 / 富媒体 | 后置 |

---

## 3. 兜底矩阵（实现核对）

| 场景 | 实现 | 主路径是否阻断 |
|------|------|:--------------:|
| LLM primary 失败 | `ModelRouter.call_with_fallback` | 否（走 fallback） |
| 订单 webhook 超时/5xx/未配置 | mock + `data_source=mock` | 否 |
| 连接器上游失败 | mock 降级 | 否 |
| Notify webhook 失败 | `emit_safe` + log | 否 |
| Gap / agent_run / cost 写失败 | try/except best-effort | 否 |
| 转人工无人认领 | timeout → 工单 + 回 AI | 否（环闭合） |
| SLA 违约 | 扫描 + notify | 否 |
| 检索/DB down | health 503；问答依赖 DB | 是（正确） |
| Prompt 注入 | Harness 硬停 | 是（安全） |
| 会话已转人工 | 固定文案、不调 AI | 是（正确） |

**红线遵守情况：** 弱证据拒答、mock 不伪装为真数据（字段层）、旁路失败不抬主路径成功 — **符合**设计原则。

---

## 4. 本审查落地代码

| 变更 | 用途 |
|------|------|
| `middleware/rate_limit.py` | IP 分钟级限流 → 429 |
| `workers/enterprise_jobs.py` | 周期 handoff 超时 + SLA 扫描 + 通知 |
| `main.py` lifespan | 非 test 启动后台任务 |
| `METRICS_TOKEN` | 生产 like 可选保护 /metrics |
| `POST /admin/system/enterprise-jobs/run` | 运维手动跑一轮 |

---

## 5. 试点上线前最小检查

- [ ] `ASKFLOW_ENV=production` + 强 `SECRET_KEY`  
- [ ] `OIDC_ISSUER` / `OIDC_CLIENT_ID`，**禁止** `OIDC_MOCK=1`  
- [ ] `DISABLE_LOCAL_REGISTER=1`（若强制 SSO）  
- [ ] `NOTIFY_WEBHOOK_*` 可达并验签  
- [ ] `FEISHU_VERIFICATION_TOKEN`（若开飞书）  
- [ ] `/metrics` 仅内网或配 `METRICS_TOKEN`  
- [ ] 确认 sweeper 日志有 `enterprise jobs ok` 或 cron 调 `enterprise-jobs/run`  
- [ ] 抽测：拒答、mock 订单、handoff 超时建单、跨访客 403  

---

## 6. 结论

| 维度 | 评级 |
|------|------|
| 业务闭环 | **B+**（代码环闭合；依赖配置与后台任务） |
| 安全 | **B**（核心护栏齐；集群限流与 metrics 暴露靠运维） |
| 兜底 | **A-**（主路径降级清晰） |
| GA | **未宣称** — 需真实 IdP、负载、渗透 |
