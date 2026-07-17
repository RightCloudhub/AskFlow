# PR / 设计拆分 — Pilot P0 + Ops P1

有序切片（可单 PR 合入，但 review 按此边界）：

| # | 切片 | 内容 | 验收锚点 |
|---|------|------|----------|
| 1 | CI | `.github/workflows/ci.yml`：api pytest + offline eval + web build | Actions 失败即挡 PR |
| 2 | OIDC JWKS | `jwks.py` + `oidc.py` 生产路径；本地 RSA 单测 | 签名/过期/aud 拒绝；mock 仍通 |
| 3 | Notify + Connectors pilot | test-emit/logs API；`pilot-integration.md`；invoke 保持 | HMAC + ≥2 连接器可试调 |
| 4 | Admin Teams / SLA UI | Teams/SLA 页 + `/sla/status` | 运营无需 curl |
| 5 | Agent Run 回放 | `agent_runs` 落库 + admin API + UI | 按 run_id 看 steps + cost |

依赖：1 可并行；2–3 无先后；4 依赖 3 的 SLA/notify 可用；5 依赖 chat side-effect 链。

非目标（本波不做）：Widget/企微飞书、质检/SIEM/i18n/富媒体、真实云 IdP CI。
