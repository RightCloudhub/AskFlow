# 全功能可插拔 — 工程量估算

| 项 | 内容 |
|----|------|
| **产品** | AskFlow（`docs/prd/PRD.md` v1.1） |
| **估算日期** | 2026-07-18 |
| **基线代码** | 后端 ~7.5k LOC / ~195 py；前端 ~1.3k LOC；Admin ~20 路由；领域服务 ~15 |
| **约束叠加** | [code-metrics.md](./code-metrics.md) 强制指标（函数 ≤50 / 文件 ≤300 / 嵌套 ≤3 / 参数 ≤3 / CC ≤10 / 禁魔数） |
| **口径** | 1 人日 = 资深全栈有效 1 天；含联调与回归；**不含**真实客户 IdP/CRM 接入 |

---

## 1. 「可插拔」定义（三级）

| 级别 | 含义 | 交付物 | 推荐 |
|:----:|------|--------|:----:|
| **L1 开关级** | 功能可关：不挂路由、pipeline 短路、UI 隐藏 | `features.yaml` + 启动期装配 | 快速裁剪 |
| **L2 模块级** | 标准 SPI：路由 / 模型声明 / pipeline 节点 / 工具 / Admin 页可注册 | `Plugin` 接口 + 内置包按域拆分 | **产品化目标** |
| **L3 运行时插件** | 第三方 wheel/目录热加载、版本隔离 | entry_points + 签名白名单 | 一般客服中台**过度** |

**本估算默认目标：L2（全量现有能力可关、可组合）。**  
L3 仅对 Tool/Connector 预留扩展口，不全量热插拔。

---

## 2. 现状可插拔成熟度

| 维度 | 现状 | 成熟度 |
|------|------|:------:|
| Tool Registry + MCP 白名单 | 有 | ★★★ |
| 意图/路由 YAML 契约 | 可配置，非插件 | ★★ |
| HTTP 连接器配置化 | 有 | ★★ |
| Model purpose→model | 配置级 | ★★ |
| API / Admin 装配 | 硬编码 `include_router` | ★ |
| `MessagePipeline` | RAG/tool/ticket/handoff 写死 if-else（341 行 / handle 220 行） | ★ |
| ORM / 迁移 | 单库全量模型 | ★ |
| 前端 Admin 导航 | NavLink 写死 | ★ |
| Feature flag | 零散 env（MCP/OIDC…） | ★☆ |
| 动态 entry_points | 无 | ☆ |

**结论：** 已有「配置半插拔」；缺统一 **Plugin SPI + 装配器 + Pipeline 节点注册表**。

---

## 3. 建议插件边界（~15 能力包）

```
[core]     auth · chat · health · audit 基础 · RBAC
 ├── [rag]         检索 · 索引 · 文档 · grounding
 ├── [agent]       harness · intent · router · loop · model_router
 │    └── [tools]  registry · order · knowledge · MCP
 ├── [ticket]      工单 · 看板
 ├── [handoff]     接管 · 超时清扫
 ├── [knowledge]   gap · draft · 知识环
 ├── [ops]         intents / prompts 运营配置
 ├── [sla]         SLA（依赖 ticket）
 ├── [notify]      通知（事件订阅）
 ├── [sso]         OIDC
 ├── [teams]       技能组（依赖 handoff）
 ├── [connectors]  业务连接器
 ├── [cost]        成本台账
 ├── [launch]      Launch Card
 └── [analytics]   看板指标
```

官方组合 profile（避免 2^N 测试爆炸）：

| Profile | 包含（示意） |
|---------|----------------|
| `core-only` | core |
| `mvp` | core + rag + agent + tools + ticket + handoff + knowledge + ops + cost |
| `enterprise` | mvp + sla + notify + sso + teams + connectors + launch + analytics + mcp |
| `full` | enterprise 全集 |

---

## 4. 工作分解与人日（L2）

> **硬性指标税：** 拆模块时须同时满足 code-metrics（小函数/小文件）。  
> 相对「只搬家不修度量」约 **+15%～25%** 已计入下表偏高档。

### 4.1 平台底座（一次性）

| 工作包 | 内容 | 人日 |
|--------|------|:----:|
| SPI 设计 | `Plugin`：id / depends / provides；`register`→`boot`→`shutdown` | 3–5 |
| Manifest | `features.yaml` + env 覆盖；依赖解析与冲突报错 | 2–3 |
| 后端装配器 | 条件路由、服务容器、可选 worker | 4–6 |
| Pipeline 插件化 | `RouteHandler` 注册表替换 runner if-else（兼修 metrics 违规） | 8–12 |
| Tool/Connector SPI 统一 | 扩展现有 Registry；声明式适配 | 3–5 |
| 配置分区 | 模块 settings 子树；禁用模块不校验其必填 | 2–3 |
| 可观测 | 指标/审计打 `plugin_id`；`/health` 列已加载插件 | 2–3 |
| 文档与契约 | 插件手册、依赖图、与 cold contract 对齐 | 3–4 |
| **小计底座** | | **27–41** |

### 4.2 现有能力拆包

| 模块 | 难度 | 人日 | 备注 |
|------|:----:|:----:|------|
| core（auth/chat/health） | 中 | 4–7 | chat 对 pipeline 依赖反转 |
| rag + embedding + documents | 中高 | 7–10 | worker 可选；pipeline 节点独立 |
| agent（intent/loop/harness） | 高 | 9–14 | 关 agent 时需 FAQ 直连 RAG 模式 |
| tools + MCP | 低中 | 3–5 | Registry 已有基础 |
| ticket | 中 | 4–6 | 侧效应与 pipeline 解耦 |
| handoff + sweeper | 中高 | 5–8 | WS / 超时任务可选挂载 |
| knowledge loop | 中 | 4–6 | gap/draft 与发布回调 |
| ops（intents/prompts） | 低中 | 3–4 | Admin 条件挂载 |
| sla | 低 | 2–3 | 相对独立 |
| notify | 低 | 2–3 | 事件总线 |
| sso | 低中 | 2–4 | 与 auth 交织 |
| teams | 低中 | 2–3 | 依赖 handoff |
| connectors | 低 | 2–3 | 配置化较好 |
| cost | 低中 | 2–4 | 埋点改钩子 |
| launch card | 低 | 1–2 | 已独立 |
| analytics | 中 | 3–5 | 指标随插件增减 |
| **小计拆包** | | **55–87** |

### 4.3 数据层 + 前端

| 工作包 | 内容 | 人日 |
|--------|------|:----:|
| ORM 可选模型 | 插件声明 metadata；迁移策略文档化 | 5–8 |
| 迁移策略拍板 | 「关插件仍留表」vs「可选迁移」 | 2–3 |
| 前端 Feature 路由 | manifest → Admin 导航 + lazy route | 4–6 |
| 前端模块边界 | `features/*` 按域拆；遵守文件 ≤300 | 5–8 |
| 用户台条件 UI | 无 ticket/handoff 时隐藏 | 2–4 |
| **小计** | | **18–29** |

### 4.4 质量 / CI / 安全

| 工作包 | 内容 | 人日 |
|--------|------|:----:|
| Profile 矩阵测 | 固定 4 档：core-only / mvp / enterprise / full | 8–12 |
| 改造现有 pytest | fixture 注入插件集；关模块断言 404 | 5–8 |
| Eval + CI | 按 profile 子集；GitHub Actions | 3–5 |
| 安全 | 禁用插件不可直调 API；权限面收敛 | 2–4 |
| code-metrics 回归 | 新代码强制绿；热点不因插件化继续膨胀 | 2–3 |
| **小计** | | **20–32** |

---

## 5. 总表

### 5.1 L2 全量（推荐产品目标）

| 范围 | 低（人日） | 高（人日） | 约人周（1 人） |
|------|----------:|----------:|:-------------:|
| 底座 SPI + Pipeline | 27 | 41 | 5–8 |
| 全模块拆包 | 55 | 87 | 11–17 |
| 数据 + 前端 | 18 | 29 | 4–6 |
| 测试 / CI / 安全 / metrics | 20 | 32 | 4–6 |
| **合计 L2** | **~120** | **~190** | **~24–38 周** |
| 2 人并行 | | | **~13–22 周** |
| 3 人（核 + 域 + 前端/测） | | | **~9–15 周** |

**约 0.65～1.05 人年。**

### 5.2 其他目标对照

| 目标 | 人日 | 说明 |
|------|-----:|------|
| **仅 L1 开关**（env/manifest 关路由+UI，pipeline 大分支） | **28–45** | 快、债多 |
| **L2 全量**（上表） | **120–190** | 推荐 |
| **L2 + Tool/Connector 热加载（局部 L3）** | **+20–35** | 签名白名单 |
| **全能力 L3 热插拔 + 版本隔离** | **210–340+** | 不建议本 PRD |
| **仅 enterprise 可裁剪（P0–P2）** | **55–75** | 性价比最高的第一刀 |

### 5.3 与 code-metrics 整改的关系

| 项 | 人日 | 关系 |
|----|-----:|------|
| 指标收敛 B1–B5（见 [code-metrics-audit.md](./code-metrics-audit.md)） | 8–14 | **可并入** Pipeline 插件化 / 核心拆函数，避免拆两次 |
| 若先 metrics 再插件化 | +0～5 | 顺序更稳 |
| 若只插件化不修 metrics | 底座偏低档，但会继续 FAIL 指标门禁 | 不推荐 |

---

## 6. 推荐分期（控制风险）

| 阶段 | 目标 | 人日 | 可验证产出 |
|:----:|------|-----:|------------|
| **P0** | Manifest + 条件路由 + Admin/前端隐藏 | 12–18 | `FEATURES=rag,ticket` 面收敛 |
| **P1** | Pipeline `RouteHandler` 注册表（顺带消 runner 超标） | 12–18 | 关 tool 不走订单路径；file/func 指标改善 |
| **P2** | enterprise 插件包（sla/sso/teams/notify/connectors/mcp/launch/cost） | 25–35 | enterprise profile 可关 |
| **P3** | rag / handoff / knowledge / ops / agent 边界 | 32–48 | `faq-only` / `mvp` 可交付 |
| **P4** | 可选模型策略 + 4 profile 测 + CI + metrics 绿 | 22–32 | 矩阵绿 + 门禁 |
| **P5**（可选） | 外部 tool/connector 加载 | 15–25 | 第三方订单插件样例 |

| 里程碑 | 累计人日 | 业务价值 |
|--------|--------:|----------|
| P0–P1 完成 | **~25–35** | 可开关 + 核心可扩展点 |
| P0–P2 完成 | **~55–75** | **企业层可裁剪（推荐试点）** |
| P0–P4 完成 | **~120–190** | L2 全量可插拔 |
| +P5 | **~135–215** | 局部生态扩展 |

---

## 7. 主要风险（抬高人日的因素）

1. **Chat ↔ Pipeline ↔ Handoff/Ticket 循环依赖** — 必须先端口/事件抽象。  
2. **关 RAG / 关 Agent 的产品语义** — 需定义 stub 或非法 profile 启动失败规则。  
3. **数据库策略** — 可选表迁移复杂；全量 schema 则「拔插件」不彻底。  
4. **测试矩阵** — 必须锁 3～5 个官方 profile，禁止全组合。  
5. **PRD 冷契约** — 插件增 intent/route 仍须契约+测试冷更新。  
6. **硬性指标** — 插件框架自身也须 ≤300 行/文件、≤50 行/函数，禁止再造巨型 `runner`。  
7. **FastAPI 参数指标** — 路由 `Depends` 与「位置参数 ≤3」冲突，须在规范中明确例外或统一 request model（见 code-metrics 审计）。

---

## 8. 结论（直接数字）

| 问题 | 答案 |
|------|------|
| 现有**全部功能**做成 **L2 可关可组合** | **约 120–190 人日（0.65–1.05 人年）** |
| **企业增强可裁剪**（P0–P2，性价比最优） | **约 55–75 人日（2.5–4 人月）** |
| 仅 **L1 feature flag** | **约 28–45 人日** |
| **L3 全量热插拔平台** | **约 210–340+ 人日，不建议** |

**投入产出建议：**  
先做 **P0 Manifest + P1 Pipeline 注册表**（约 1～1.5 人月），同时消化 `runner.py` / 会话主路径的 code-metrics 违规；再按交付需要做 enterprise 裁剪（P2），最后才考虑 faq-only 级核心拆包（P3–P4）。

---

## 9. 相关文档

| 文档 | 关系 |
|------|------|
| [code-metrics.md](./code-metrics.md) | 实现时强制遵守的度量 |
| [code-metrics-audit.md](./code-metrics-audit.md) | 当前违规热点（可与 P1 合并整改） |
| [../prd/PRD.md](../prd/PRD.md) | 能力清单与分期 |
| [../STATUS.md](../STATUS.md) | 功能完成状态（可插拔 ≠ 功能未完成） |
| [../prd/STRUCTURE.md](../prd/STRUCTURE.md) | 目录域，插件包应对齐 |
