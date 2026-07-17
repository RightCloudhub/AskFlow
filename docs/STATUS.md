# AskFlow 项目完成状态

| 项 | 内容 |
|----|------|
| **产品** | AskFlow — 企业智能客服（RAG + Agent） |
| **对照 PRD** | `docs/prd/PRD.md` v1.1 |
| **完成线** | **§12.1 MVP + §12.2 + 试点 + Widget + 飞书 + 质检骨架 + SIEM** |
| **文档日期** | 2026-07-18 |
| **整体状态** | **PILOT-READY + MULTI-CHANNEL（代码）** |
| **对照 PRD** | `docs/prd/PRD.md` **v1.3** |

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
| PR 拆分 | `docs/engineering/pr-split-pilot-p0-p1.md` |

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

---

## 4. 验证记录

| 检查 | 结果 |
|------|------|
| `pytest` (apps/api) | **99+ passed**（含 JWKS / run replay / notify） |
| Eval runner | **passed=8 failed=0** |
| Web build | **success** |
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

详见：`deploy/checklists/pilot-integration.md`
