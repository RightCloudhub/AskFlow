# AskFlow 项目完成状态

| 项 | 内容 |
|----|------|
| **产品** | AskFlow — 企业智能客服（RAG + Agent） |
| **对照 PRD** | `docs/prd/PRD.md` v1.1 |
| **完成线** | **§12.1 MVP + §12.2 + 试点 + Widget + 飞书 + 质检骨架 + SIEM** |
| **文档日期** | 2026-07-18 |
| **整体状态** | **PILOT-READY + MULTI-CHANNEL（代码）** |
| **对照 PRD** | `docs/prd/PRD.md` **v1.3** |
| **闭环/安全审查** | `docs/engineering/business-loop-security-fallback-review.md` |
| **安全 pre-commit** | `docs/engineering/security-precommit-checklist.md` |

---

## 1. 范围说明

| 范围 | 状态 | 说明 |
|------|------|------|
| PRD **§12.1** MVP 16 条 | ✅ | 基线保持 green |
| PRD **§12.2** 企业 13 条 | ✅ **代码完成** | SLA/通知/SSO/连接器/技能组/OOS/eval/用户治理/成本/Launch Card/MCP 等 |
| PRD §11.2 排除项 | 不做 | 多租户计费、语音 CC、无限自主 Agent 等 |
| 真实 OIDC JWKS | ✅ 代码 | RS256 + iss/aud/exp；本地 RSA 单测；生产配 `OIDC_ISSUER`/`OIDC_CLIENT_ID` |
| GitHub Actions | ✅ | `.github/workflows/ci.yml`：pytest + eval + web build |
| Admin Teams / SLA / Agent Runs | ✅ | 运营可自助；S-08 按 run_id 回放 |
| Web Widget（E7a / U-11） | ✅ | 访客 session + 同流水线；`/widget` + `public/embed-snippet.html` |
| SIEM 审计导出（E9 部分） | ✅ | `GET/POST /admin/audit-logs/export-siem`；`SIEM_WEBHOOK_URL` |
| 飞书通道（E7b / U-12） | ✅ | `POST /channels/feishu/events`；challenge + 同流水线回复 |
| 质检 QC（E8 骨架） | ✅ | `/admin/qc/summary|low-quality` + Admin 质检页 |
| E9 扩展 PII | ✅ | 订单号部分遮罩 + 身份证/银行卡/地址；审计 `mask_detail` |
| E10 知识 diff/回滚 | ✅ | revision 快照 + `/admin/documents/{id}/generations|diff|rollback` |
| E12 多 worker cancel | ✅ | `cancel_registry`（进程 + 可选 Redis）+ 生成中止 + metrics |
| E15 运维 Runbook | ✅ | `deploy/runbooks/reindex-model-storage.md` · `multi-worker-cancel-metrics.md` |
| E3 最少未结派单 | ✅ | `TeamService.least_open_member` · `GET /admin/teams/{id}/suggest-assignee` |
| E25 检索缓存 | ✅ | `rag/retrieval_cache.py` · `RETRIEVAL_CACHE_TTL_S` · metrics hit/miss |
| E26 会话中段摘要 | ✅ | `agent/history_summary.py` · harness `history_summarized` |
| 企微 / 钉钉通道 | ✅ | `/channels/wecom` · `/channels/dingtalk` · 同流水线 |
| E16 附件元数据 | ✅ | `chat/attachments.py` · 消息 meta + 文本 cue |
| E17 i18n | ✅ | `services/i18n/messages.py` zh-CN / en-US |
| E18 多 Bot | ✅ | `bots/profiles.py` · `GET /admin/bots` · `BOT_PROFILES_JSON` |
| E19 访客 | ✅ | Widget（既有） |
| E27 扩展推理 | ✅ | 默关 `REASONING_ENABLED` · 意图白名单 + 步数预算 |
| E28 沙箱 | ✅ | 默关 `SANDBOX_ENABLED` · sandbox_* 工具拒绝 |
| E29 前端打磨 | ✅ | `theme.css` 品牌渐变/动效 + reduced-motion |

---

## 2. §12.2 企业验收对照

| # | §12.2 标准 | 状态 | 实现 |
|---|------------|:----:|------|
| 1 | SLA 主动升级 + 离线通知 | ✅ | `SLAEngine`；`NotifyService` HMAC webhook + test-emit |
| 2 | SSO + 角色映射 | ✅ | OIDC mock/JIT + **JWKS 生产校验** |
| 3 | ≥2 业务连接器 | ✅ | `order_status` + `crm_lookup`；Admin 试调用 |
| 4 | 技能组 | ✅ | Team API + **Admin Teams 页** |
| 5 | out_of_scope | ✅ | 意图 + `refuse` 路由 |
| 6 | 用户管理 + 导出/删除 | ✅ | list/disable/export/delete |
| 7 | 主路径自动化 + eval | ✅ | pytest + **CI 跑 eval** |
| 8 | 多 worker 安全 | ✅ | handoff claim/sweep CAS |
| 9 | §9 指标 Admin 可见 | ✅ | analytics + Prometheus |
| 10 | 多模型 fallback | ✅ | `ModelRouter.call_with_fallback` |
| 11 | Launch Card | ✅ | CRUD + measure |
| 12 | MCP 白名单 + 审计 | ✅ | `/admin/mcp/sync` |
| 13 | 成本可汇总 | ✅ | CostLedger + `/admin/costs/summary` |

---

## 3. 试点接入落点（本波）

| 能力 | 路径 |
|------|------|
| OIDC JWKS | `app/services/auth/jwks.py` · `oidc.py` |
| Notify pilot | `api/v1/admin/notify` test-emit/logs · `deploy/checklists/pilot-integration.md` |
| Connectors | Admin 试调用 + 文档 |
| CI | `.github/workflows/ci.yml` |
| Teams / SLA UI | `apps/web/.../TeamsPage.tsx` · `SlaPage.tsx` |
| Agent Run 回放 | `models/agent_run.py` · `run_store.py` · `/admin/agent-runs` · `AgentRunsPage.tsx` |
| Web Widget | `services/widget/` · `api/v1/widget` · plugin `widget` · `WidgetPage.tsx` |
| SIEM | `services/audit/siem.py` · audit export routes |
| 飞书 | `services/channels/feishu/` · `api/v1/channels/feishu` · plugin `feishu` |
| 质检 | `services/qc/` · `api/v1/admin/qc` · `QcPage.tsx` |
| 限流 / 后台扫描 | `middleware/rate_limit.py` · `workers/enterprise_jobs.py` |
| PR 拆分 | `docs/engineering/pr-split-pilot-p0-p1.md` |
| 闭环·安全·兜底审查 | `docs/engineering/business-loop-security-fallback-review.md` |

### 环境变量（生产）

| 变量 | 用途 |
|------|------|
| `NOTIFY_WEBHOOK_URL` / `NOTIFY_WEBHOOK_SECRET` | 出站通知 |
| `OIDC_ISSUER` / `OIDC_CLIENT_ID` / `OIDC_MOCK` | SSO（生产关 mock） |
| `DISABLE_LOCAL_REGISTER` | 强制 SSO |
| `MCP_ENABLED` / `MCP_TOOL_WHITELIST` | MCP 工具白名单 |
| `SIEM_WEBHOOK_URL` | 审计日志 SIEM 推送（可选） |
| `FEISHU_VERIFICATION_TOKEN` | 飞书事件订阅校验 |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 飞书主动回复（可选；未配则仅本地流水线） |
| `SWEEPER_ENABLED` / `SWEEPER_INTERVAL_SECONDS` | 后台 handoff 超时 + SLA 扫描（test 自动关） |
| `RATE_LIMIT_PER_MINUTE` | IP 限流（默认 60；test 跳过） |
| `METRICS_TOKEN` | 生产 like 下可选保护 `/metrics` |

---

## 4. 验证记录

| 检查 | 结果 |
|------|------|
| `pytest` (apps/api) | **156+ passed**（含 E9/E10/E12 波次缺口 + RAG/向量/索引） |
| Eval runner | **passed=8 failed=0** |
| Web build | 见最新 CI / 本地 `npm run build` |
| CI workflow | 文件就位：api-pytest + offline-eval + web-build |

复跑：

```bash
cd apps/api && source .venv/bin/activate
PYTHONPATH=. pytest -q
PYTHONPATH=. python ../../evals/runners/run_eval.py
cd ../web && npm run build
```

---

## 5. 状态码

| 码 | 含义 |
|----|------|
| `MVP-COMPLETE` | §12.1 |
| `ENTERPRISE-READY` | §12.2 代码层 |
| **`PILOT-READY`** | 试点接入代码 + CI + 运营自助 UI 已交付 |
| `GA-CERTIFIED` | 未宣称（需真实 IdP/负载/渗透与合同 SLA 取证） |

---

## 6. 可插拔（L2）进度

| 阶段 | 状态 | 说明 |
|------|:----:|------|
| P0 Manifest + 条件路由 + Admin/前端隐藏 | ✅ | `packages/contracts/features.yaml` · `app/plugins/*` |
| P1 Pipeline RouteHandler + side effects | ✅ | 含 `agent_run` side effect |
| P2–P4 企业/核心域深拆 + profile 矩阵 CI | ⏳ | 骨架已就绪 |
| 文档 | ✅ | `docs/architecture/plugins.md` |

---

## 7. 已知生产接入项（配置/客户侧）

1. 配置客户真实 IdP 的 `OIDC_ISSUER` + `OIDC_CLIENT_ID`（代码已校验 JWKS）  
2. 配置可达的 `NOTIFY_WEBHOOK_URL` 与密钥  
3. 连接器 `base_url` 指向客户内网 CRM/订单系统  
4. Prometheus 抓取 `/metrics` 与告警规则挂载  
5. 生产 `SECRET_KEY` 强度与 `ASKFLOW_ENV=production` fail-safe  
6. 可选 LLM：`LLM_BASE_URL` + `LLM_API_KEY`（生成/流式；未配则抽取式）  
7. 可选向量：`EMBEDDING_*` 与 `CHROMA_HOST`/`CHROMA_PERSIST_DIR`（未配则 offline hash + 内存索引）  
8. 可选异步索引：`INDEX_ASYNC=1` +（可选）`REDIS_URL`；进程内 `index_worker` 默认随 API 启动  

详见：`deploy/checklists/pilot-integration.md`

---

## 8. RAG / 索引增强（2026-07-18）

| 能力 | 状态 | 路径 |
|------|:----:|------|
| 真实 embedding 客户端 | ✅ | `services/rag/embedding/`（OpenAI 兼容 + offline） |
| 向量通道（非 BM25 占位） | ✅ | `services/rag/vector/` memory cosine + 可选 Chroma |
| LLM 生成 / 流式 | ✅ | `services/llm/client.py` · `rag/generator` |
| 异步 index worker | ✅ | `workers/index_worker/` 队列消费 chunk→embed→upsert |
| Indexer 双写 BM25+vector | ✅ | `services/knowledge/indexer/service.py` |

---

## 9. 范围诚实声明

| 项 | 状态 |
|----|------|
| §12.1 + §12.2 代码验收 | ✅ 有真实路径与自动化 |
| §10 非可选残留 E9/E10/E12/E15 | ✅ 本波收口 |
| §11.2 排除项 | 不做 |
| 企微/钉钉 | ✅ 代码通道（与飞书并列） |
| E16–E19 / E29 P2 | ✅ 代码层交付（品牌动效为 CSS 级） |
| E27/E28 | ✅ 默关可开；非生产默开 |
| L2 插件 P2–P4 深拆 | ⏳ 骨架 + profile 解析；非全矩阵隔离 |
| E20 多租户 SaaS | 不做（§11.2） |
| **GA-CERTIFIED** | 未宣称（需真实 IdP/负载/渗透） |
