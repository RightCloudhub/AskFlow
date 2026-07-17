# Launch Card 检查清单

> 来源：PRD v1.1 §4.18、附录 F。  
> 适用：Prompt 激活、模型路由、Loop 预算、Grounding 阈值、新工具/MCP。

## 上线前

- [ ] 变更类型与一句话摘要
- [ ] 离线 eval before/after（golden + refusals）
- [ ] 预期指标：解答率 / 拒答率 / 👍 / 单位成本 / TTFT
- [ ] 风险与回滚步骤（谁执行、多长时间）
- [ ] 观察窗口（建议 24–72h）
- [ ] 方案权衡（附录 E）已记录（重大变更）

## 上线后

- [ ] 窗口结束拉取实测指标
- [ ] 结论：达标 / 观察 / 回滚
- [ ] 若回滚：确认旧 Prompt/模型已生效并留审计

## 模板

见 PRD 附录 F；产品化后迁入 Admin `launch-cards`。
