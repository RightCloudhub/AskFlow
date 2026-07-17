# 告警规则建议

> 试点期可先「文档化阈值 + 人工看盘」；生产再落 Alertmanager。  
> 规则草稿目录：`infra/prometheus/rules/`。

---

## 1. 严重级别

| 级别 | 含义 | 响应 |
|------|------|------|
| **critical** | 用户大面积不可用 | 立即值班 |
| **warning** | 降级或体验恶化 | 工作时间处理 |
| **info** | 趋势关注 | 周会回顾 |

---

## 2. 基础设施

| 告警 | 条件（建议） | 级别 |
|------|--------------|------|
| APIDown | `up{job="askflow"}==0` 持续 2m | critical |
| DependencyDown | `askflow_dependency_up==0` 持续 2m | critical |
| HighHTTP5xx | 5xx rate &gt; 5% 持续 5m | critical |
| HighLatencyP95 | HTTP P95 &gt; 5s 持续 10m | warning |

---

## 3. LLM / RAG

| 告警 | 条件 | 级别 |
|------|------|------|
| LLMErrorSpike | `llm_error` 5m 速率 &gt; 基线 3× 或 &gt; 10/min | warning |
| TTFTDegraded | `ttft` P95 &gt; 3s 持续 15m | warning |
| RefusalCollapse | 拒答率相对 7d 基线下降 &gt; 50% 且 traffic 正常 | warning（防胡编） |
| RefusalSpike | 拒答率 &gt; 60% 持续 30m | warning（知识空洞） |
| CitationFailSpike | oob/skipped 占比 &gt; 20% | warning |

---

## 4. Handoff / Ticket

| 告警 | 条件 | 级别 |
|------|------|------|
| HandoffQueueBacklog | `queue_depth` &gt; 20 持续 10m | warning |
| HandoffTimeoutSpike | timeout 速率 &gt; 5/h | warning → 有通知中心后可 critical |
| TicketOldestOpen | 业务查询 oldest open &gt; SLA（MVP 24h） | info/warning |

---

## 5. 索引

| 告警 | 条件 | 级别 |
|------|------|------|
| IndexQueueStuck | 最老 pending 年龄 &gt; 30m | warning |
| IndexFailRate | fail ratio &gt; 10% 1h | warning |

---

## 6. 安全与配置

| 告警 | 条件 | 级别 |
|------|------|------|
| HarnessInjectionSpike | `prompt_control_request` 等 flag 突增 | warning |
| WebhookFailHigh | order webhook fail &gt; 30% 15m | warning |
| AuthFailSpike | WS/HTTP 401 异常升高 | info |

**不靠告警：** 默认 SECRET 生产启动失败——属于部署门禁。

---

## 7. 静默与抑制

- 维护窗口抑制 Index/LLM  
- 依赖 down 时抑制衍生 LLM/RAG 告警  
- 单实例试点可关闭多副本相关规则  

---

## 8. 通知通道（Wave A E2）

MVP：日志 + 值班看 Grafana。  
v2：邮件 / IM Webhook / 工单自动建单；HMAC 签名出站。
