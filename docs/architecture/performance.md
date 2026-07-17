# 性能优化

> 产品对齐：PRD §8.4、§4.2、§4.15。  
> 原则：**先保正确与可降级，再压延迟与成本；优化必须可度量。**

---

## 1. 目标（建议值，非合同 SLA）

| 指标 | 目标 | 备注 |
|------|------|------|
| 首 token（TTFT） | P95 &lt; 3s | 不含冷启动 LLM |
| 非流式工具查询 | P95 &lt; 2s + 外部 webhook | |
| 意图分类 | P95 &lt; 1.5s | 规则命中应 ≪ 此值 |
| 文档上传 API | P95 &lt; 2s | 索引异步 |
| 单次 run 墙钟 | &lt; 45s 硬顶 | 防挂死 |
| 并发 WS | 单实例数百级 | 需压测验证 |

**成本代理指标：** 每有效会话 token 数、生成 LLM 调用次数（拒答应为 0 次生成）。

---

## 2. 延迟预算（幸福路径 FAQ）

| 阶段 | 预算指引 | 优化杠杆 |
|------|----------|----------|
| 鉴权 / 读会话 | &lt; 50ms | 连接池、必要字段 |
| Harness + 历史裁剪 | &lt; 20ms | 纯本地 |
| 意图（规则） | &lt; 5ms | 关键词表 |
| 意图（LLM） | 200–800ms | **小模型**；规则优先 |
| 查询改写 | 0–50ms 规则；LLM 则另计 | **默认规则，关 LLM 改写** |
| BM25 | 20–100ms | 索引内存/进程内 |
| 向量检索 | 50–200ms | top_k、维度、过滤 |
| Grounding | &lt; 5ms | 本地阈值 |
| 首 token | 视模型 | 流式；短 system；少 chunk |
| 生成余下 | 用户可感知流式 | max_tokens 上限 |

弱证据拒答路径应 **跳过生成**，整轮常 &lt; 500ms（视检索）。

---

## 3. 优化策略（按收益排序）

### 3.1 少做贵事（最高收益）

| 策略 | 做法 |
|------|------|
| 拒答不调生成 LLM | grounding 失败直接固定文案 |
| 规则优先于模型 | 意图关键词、订单号正则、同义改写表 |
| 小模型干小活 | classify / summary /（可选）rewrite 与 generate 分离 |
| transferred 不进 AI | 零模型调用 |
| 槽位续跑跳过分类 | 已挂起 tool 时少一轮 LLM |

### 3.2 上下文与检索瘦身

| 旋钮 | 建议默认 | 性能影响 |
|------|----------|----------|
| 历史条数 | 12 | 降 prompt tokens |
| 单条字符 | ~1200 | |
| 进生成 chunk 数 | 6 | 降 TTFT 与费用 |
| chunk 截断 | ~800 字 | |
| 生成 max_tokens | 按场景收紧 | 降尾延迟 |
| top_k BM25/向量 | 适度（如 8–20）再融合截断 | 降检索 CPU |

详见 `context-engineering.md`。

### 3.3 异步与非阻塞

| 路径 | 要求 |
|------|------|
| 文档索引 | 上传只入队；HTTP 秒回 |
| Gap 信号 / 部分 analytics | best-effort，失败不挡回复 |
| Handoff 摘要 | 硬超时（如 8s），超时空摘要仍入队 |
| 引用自检 | 可超时跳过并打标 |

### 3.4 连接与运行时

| 项 | 建议 |
|----|------|
| DB | async 池；避免 N+1 拉历史 |
| Redis | 限流、队列、pub/sub；关键路径设超时 |
| HTTP 出站 | 全局 timeout；连接复用 |
| 流式 WS | 尽早 flush 首 token；支持 cancel 取消生成 |
| Embedding | 相同文本可进程内/Redis 短缓存（索引侧更有用） |

### 3.5 缓存（谨慎启用）

| 缓存 | MVP | 说明 |
|------|-----|------|
| 厂商 prompt 前缀稳定 | ✅ 约定 | system 模板少变，利官方 cache |
| Embedding 去重 | 建议 | 索引吞吐 |
| 检索结果 TTL | 默认关 | 政策变更风险；v1.5 可短 TTL |
| 语义复用回答 | **关** | 安全与时效 |

---

## 4. 模型侧性能与成本

```
purpose          延迟敏感    建议
─────────────────────────────────────
intent_classify  高         小模型 + Structured Outputs；规则优先
query_rewrite    高         默认规则，不用 LLM
handoff_summary  高         小模型 + 硬超时
rag_generate     中         中档流式；弱证据不调用
embedding        中         专用模型，与 chat 分离
```

Fallback：超时/5xx 切下一模型，**链耗尽 → 固定话术**，禁止无超时挂起。

---

## 5. 并发与扩展注意

| 点 | 风险 | 方向 |
|----|------|------|
| 单 worker 试点 | 简单 | 先压测再扩 |
| 索引 worker | 双消费 | 条件 claim / 锁 |
| Handoff 清扫 | 重复升级 | `SKIP LOCKED` |
| BM25 多实例 | 索引不一致 | 文档化最终一致或外置 |
| WS cancel 跨实例 | 取消耗效 | v1.5 Redis 广播 |

---

## 6. 性能反模式（禁止）

1. 默认全程旗舰模型「更聪明」  
2. 全量历史塞进每一次 classify  
3. 同步 embedding 挡上传 API  
4. 摘要失败阻塞 handoff  
5. 无墙钟上限的工具/Loop 重试  
6. 用同步 RAG 调试接口扛生产峰值  
7. Prometheus 高基数 label（user_id 等）拖垮时序库  

---

## 7. 度量与优化闭环

| 步骤 | 动作 |
|------|------|
| 1 | 看 `ttft`、`generate_duration`、`retrieval_latency`、`llm_latency` by purpose |
| 2 | 分解：模型 vs 检索 vs DB |
| 3 | 先砍调用次数，再砍 tokens，再调基础设施 |
| 4 | 回归 golden/拒答，防止「降本降质」 |

关键指标名见 `docs/observability/metrics-catalog.md`（实现时优先注册 §3–5 相关项）。

---

## 8. MVP 验收

- [ ] 弱拒答路径无生成 LLM 调用（可用 mock 计数）  
- [ ] 上传文档接口 P95 达标且索引异步  
- [ ] 订单 webhook 超时不拖死整轮（有超时）  
- [ ] cancel 能停止当前生成（单 worker）  
- [ ] 历史超 12 条时 prompt 长度仍受控（trace 可证）  

---

## 9. 压测建议（试点前）

| 场景 | 关注 |
|------|------|
| 纯 FAQ 流式 | TTFT、错误率 |
| 拒答比例 30% | 总 token 是否明显下降 |
| 工具慢（人为 3s） | 是否触发超时与降级 |
| 双坐席 handoff | claim 409、队列延迟 |
| 索引 10 大 PDF | 队列深度、API 仍轻 |

相关：`rag-pipeline.md`、`query-rewrite.md`、`security-and-fallback.md`。
