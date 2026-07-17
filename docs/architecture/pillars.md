# 三大工程支柱

AskFlow 在业务功能之外，实现与评审时优先对齐这三块：

| 支柱 | 文档 | 一句话 |
|------|------|--------|
| **安全与兜底** | [security-and-fallback.md](./security-and-fallback.md) | 硬护栏 + 可解释降级；拒答与转人优先于胡编 |
| **性能优化** | [performance.md](./performance.md) | 少调贵模型、瘦上下文、异步非关键路径；指标驱动 |
| **记忆与可观测** | [memory-and-observability.md](./memory-and-observability.md) | 有界会话记忆 + logs/metrics/trace；默认可解释 |

## 关系

```
        安全与兜底（正确优先）
              │
              │ 约束
              ▼
     记忆预算 ──► 性能（tokens/延迟）
              │
              │ 暴露
              ▼
          可观测（证明与告警）
```

- 安全策略冲突时优先级见 security 文档 §8  
- 性能优化不得突破拒答/注入硬规则  
- 可观测写入不得拖垮主路径（best-effort）  

## MVP 合并验收（抽检）

1. 注入 → 安全拒答，无生成调用  
2. 弱检索 → 拒答，TTFT 明显短于正常生成  
3. webhook 超时 → 降级文案 + metrics  
4. 长会话 → 历史裁剪，trace 可证  
5. `/health` 503 与 `/metrics` 内网可达  
6. 日志 mask + `trace_id`/`run_id`  

## PRD 锚点

| 支柱 | PRD |
|------|-----|
| 安全与兜底 | §4.3.3 Harness、§4.2 Grounding、§4.11、§8.1 |
| 性能 | §8.4、§4.15 预算 |
| 记忆与可观测 | §4.5 会话、§4.12、§4.17、§8.3 |
