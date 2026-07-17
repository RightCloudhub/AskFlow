# 监控与可观测性（Observability）

> 对应 PRD §4.12、§8.3、§9、S-02/S-03、附录 A。  
> 代码落点：`middleware/`、`api/v1/health`、`services/analytics/`、`infra/prometheus/`、`infra/grafana/`。  
> 关联：[metrics-catalog.md](./metrics-catalog.md)、[tracing.md](./tracing.md)、[alerts.md](./alerts.md)。

---

## 1. 三大支柱

| 支柱 | 用途 | 落地 |
|------|------|------|
| **Logs** | 排障、审计关联、脱敏 | JSON 结构化日志 + `trace_id` |
| **Metrics** | SLO、容量、业务健康 | Prometheus `/metrics`（网络隔离） |
| **Traces** | 单次对话决策链 | `run_id` / ContextTrace / 可选 OTel |

补充：

- **Health**：依赖探活，失败 503（`/health`）  
- **Analytics**：运营可读聚合（Admin Dashboard，非时序库替代品）  
- **Audit**：合规「谁改了什么」，与 metrics 分离  

```
请求/WS
  → middleware 注入 trace_id
  → 业务打 span 事件（intent / retrieval / llm / tool）
  → metrics 计数与直方图
  → logs 输出（mask）
  → best-effort 写 ContextTrace / analytics
```

---

## 2. 健康检查

### 2.1 `GET /health`（深度）

| 检查项 | 失败语义 |
|--------|----------|
| PostgreSQL | critical |
| Redis | critical |
| 向量库（Chroma） | critical（检索不可用） |
| 对象存储（MinIO/S3） | degraded 或 critical（上传场景） |
| 可选：LLM 探活 | **不**阻塞 ready（避免外部抖动踢掉实例） |

响应建议：

```json
{
  "status": "ok|degraded|down",
  "version": "git-sha",
  "harness_policy_version": "1.0",
  "checks": {
    "postgres": {"ok": true, "latency_ms": 3},
    "redis": {"ok": true, "latency_ms": 1},
    "vector": {"ok": true, "latency_ms": 12},
    "object_storage": {"ok": true, "latency_ms": 8}
  }
}
```

- 任一 critical 失败 → HTTP **503**  
- K8s：`liveness` 可用轻量 `/health/live`（仅进程）；`readiness` 用深度 `/health`  

### 2.2 Admin System Health（§4.12.2）

在依赖探活之上附加业务面：

| 项 | 说明 |
|----|------|
| 文档状态计数 | pending / indexing / active / failed |
| 最老 pending 年龄 | 索引积压 |
| chunk 总数、last_indexed_at | |
| 24h 审计 action 分布 | |
| open handoff / ticket 堆积 | |

---

## 3. 日志规范

### 3.1 字段约定

```json
{
  "ts": "2026-07-17T12:00:00.000Z",
  "level": "INFO",
  "msg": "rag.generate.done",
  "trace_id": "...",
  "run_id": "...",
  "conversation_id": "...",
  "user_id": "...",
  "route": "rag",
  "intent": "faq",
  "latency_ms": 820,
  "flags": [],
  "service": "api"
}
```

| 规则 | 说明 |
|------|------|
| `LOG_MASKING_ENABLED=true` | 默认开；手机号/邮箱/订单号遮罩 |
| 禁止 | 打印完整 JWT、SECRET、webhook 密钥、未脱敏 prompt 全量（生产） |
| WS | 连接、auth 成功/失败、cancel、异常断开各打一条 |
| Worker | `worker_id` + `task_id` + claim 结果 |

### 3.2 级别

| Level | 场景 |
|-------|------|
| DEBUG | 开发；检索 top 分数明细（生产默认关） |
| INFO | 正常业务里程碑 |
| WARNING | 降级：mock 订单、rewrite 失败回落、证据自检跳过 |
| ERROR | 需关注：LLM 连续失败、索引 failed、清扫异常 |
| CRITICAL | 无法服务：DB 挂、生产密钥拒启 |

---

## 4. Metrics 暴露

| 项 | 约定 |
|----|------|
| 路径 | `GET /metrics` |
| 格式 | Prometheus text |
| 鉴权 | **无** → 仅内网 / 反代 IP 允许 |
| 多 worker | v1.5 前单 worker 试点；多 worker 见 [tracing.md](./tracing.md) 与 Wave E |

完整指标清单见 [metrics-catalog.md](./metrics-catalog.md)。

---

## 5. 业务监控黄金信号

### 5.1 对话与 RAG

| 信号 | 健康方向 | 关联指标 |
|------|----------|----------|
| 首 token 延迟 | P95 &lt; 3s | `askflow_ttft_seconds` |
| 拒答率 | 稳定区间；突降可能「乱答」 | `askflow_rag_refusal_total` |
| 弱检索占比 | 与 Gap 同步看 | `grounding` 分桶 |
| 👍 / 👎 | 👎 率上升 → 知识/Prompt | feedback counters |
| LLM 失败 | 升高 → fallback 话术 | `askflow_llm_error_total` |

### 5.2 Agent / 路由

| 信号 | 说明 |
|------|------|
| intent 分布漂移 | 分类 Prompt 改坏 |
| harness 拦截突增 | 注入探测 / 客户端异常 |
| clarify 率过高 | 规则过严或模型过懵 |
| 非法 route 打回 | 配置错误 |

### 5.3 工单与 Handoff

| 信号 | 说明 |
|------|------|
| handoff queued 堆积 | 坐席不足 |
| handoff timeout 速率 | 无人值守（PRD 高风险） |
| ticket open age | SLA 事后统计（MVP） |
| claim 409 比率 | 并发抢单正常 vs 异常 |

### 5.4 索引与依赖

| 信号 | 说明 |
|------|------|
| pending 文档年龄 | worker 挂 / 队列堵 |
| index fail rate | 解析/embed 问题 |
| order webhook fail | 降级 mock 增多 |
| 依赖 probe | /health 子检查 |

---

## 6. Admin Analytics vs Prometheus

| 维度 | Admin Analytics | Prometheus |
|------|-----------------|------------|
| 用户 | 运营 / 知识管理员 | 运维 / 值班 |
| 粒度 | 近 7 日聚合、分布 | 实时时序、直方图 |
| 存储 | PG 聚合查询 | TSDB |
| 典型问题 | 「👎 为啥升了」 | 「API 是否要扩容」 |

二者指标口径应对齐同一事件源（中间件 / pipeline 埋点），避免各算各的。

---

## 7. 仪表盘规划

| Dashboard | 受众 | 面板要点 |
|-----------|------|----------|
| **AskFlow Overview** | 全员 | QPS、错误率、TTFT、在线 WS、版本 |
| **RAG Quality** | 算法/运营 | 拒答率、grounding 分桶、rewrite strategy、引用自检失败 |
| **Agent & Harness** | 研发 | intent 分布、fallback/truncate、route |
| **Handoff & Ticket** | 客服主管 | queue 深度、timeout、SLA breach 统计 |
| **Indexing** | 运维 | pending、fail、时长、chunk 增长 |
| **LLM Provider** | 运维 | 延迟、token、error by model |

Grafana 面板 JSON 预留目录：`infra/grafana/dashboards/`。

---

## 8. 与 Gap 雷达联动

监控不替代知识运营，但提供信号：

```
weak_retrieval_refusal ↑ + gap.frequency TopN
  → 运营优先补文档

prompt_control_request ↑
  → 安全关注，非知识问题

response_truncated ↑
  → 输出预算或模型啰嗦

negative_feedback ↑ on intent=faq
  → 回看最近 Prompt 版本与文档 generation
```

---

## 9. 部署与安全清单

- [ ] `/metrics` 不对公网  
- [ ] `/health` 可对 LB，勿泄露内部主机名/密钥  
- [ ] 日志外发前确认 mask  
- [ ] 试点：单 worker + 本地 Grafana  
- [ ] 生产：Prometheus + Alertmanager；告警规则见 [alerts.md](./alerts.md)  
- [ ] 默认 SECRET 生产拒启（启动即失败，不靠监控发现）  

---

## 10. MVP 最小集（先做这些）

1. JSON 日志 + `trace_id` + mask  
2. `/health` 四依赖  
3. `/metrics`：HTTP、WS、RAG、LLM、handoff timeout、index queue、webhook fail  
4. Admin Dashboard 读 PG 聚合（👎、intent、harness reason）  
5. 文档化告警阈值（即使暂未接 Alertmanager）  

v1.5+：主路径 E2E、eval CI、多 worker metrics 方案、OTel 导出可选。
