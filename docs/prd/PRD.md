# PRD：AskFlow — 企业智能客服系统（RAG + Agent Orchestration）

| 项 | 内容 |
|----|------|
| **产品名称** | AskFlow |
| **文档版本** | v1.3（飞书通道 + 质检骨架） |
| **文档类型** | 产品需求文档（Product Requirements Document） |
| **更新日期** | 2026-07-18 |
| **读者** | 产品、研发、测试、运维、试点客户 IT、Agent 平台负责人 |
| **变更摘要** | v1.3：**E7b 飞书机器人 webhook**（同 Agent 流水线）；**E8 质检汇总/低分 run**；状态见 `docs/STATUS.md` |

---

## 目录

1. [项目概览](#1-项目概览)
2. [用户角色与用户故事](#2-用户角色与用户故事)
3. [系统架构](#3-系统架构)
4. [功能需求](#4-功能需求)
5. [端到端业务旅程](#5-端到端业务旅程)
6. [数据模型](#6-数据模型)
7. [接口与集成面](#7-接口与集成面)
8. [非功能需求](#8-非功能需求)
9. [业务指标](#9-业务指标)
10. [分期路线图](#10-分期路线图)
11. [范围边界](#11-范围边界)
12. [验收标准](#12-验收标准)
13. [风险与依赖](#13-风险与依赖)
14. [附录](#14-附录)

---

## 1. 项目概览

### 1.1 背景与问题

企业客服、售后与内部 Helpdesk 普遍面临：

| # | 痛点 | 业务后果 |
|---|------|----------|
| P1 | 重复 FAQ 占用大量一线人力 | 成本高、坐席疲劳、高峰扛不住 |
| P2 | 知识散落在文档、Wiki、工单、IM | 答复不一致、新人上手慢、合规风险 |
| P3 | 关键词检索无法理解用户自由表述 | 命中率低 → 反复追问或强转人工 |
| P4 | 通用大模型易胡编政策/价格 | 客诉与法律风险 |
| P5 | 「AI → 工单 → 人工 → 知识沉淀」断环 | 同类问题反复出现，知识不增长 |
| P6 | 改话术要发版、无审计脱敏 | 运营失灵，B 端/合规审查过不了 |
| P7 | 无 SLA 主动升级、无离线通知 | 工单静默堆积，客户体验黑洞 |
| P8 | Agent 只会「单轮聊」，无规划/重试/工具失败恢复 | 复杂售后与排障场景掉链、重复追问 |
| P9 | 单一贵模型通吃；无成本与质量分流 | 单位会话成本失控，高峰不可持续 |
| P10 | 上下文窗口当无限用；无 token 预算与缓存 | 延迟与费用飙升，长会话质量崩坏 |
| P11 | 上线前无效果预估、上线后无对照验证 | 无法判断「Agent 改了啥」是变好还是变差 |

### 1.2 产品定义

**AskFlow** 是一套 **单租户、可私有化部署** 的智能客服中台，并以 **自研 Agent 编排层（Orchestration）** 为中枢——覆盖方案选型、架构、开发、上线与效果复盘的完整责任链，而非简单封装现成 Agent 框架。

**核心公式：**

```
私有知识库 RAG（可引用、可拒答）
  + 自研 Agent Loop（规划 · 执行 · 纠错 · 工具调用闭环）
  + Cognitive Harness（输入 · 路由 · 输出安全护栏）
  + 多模型路由与成本调度（按场景选型，非永远最贵）
  + Prompt / 上下文工程（预算 · 缓存 · 长会话状态）
  + 工具链（业务 webhook · MCP · 可选沙箱）
  + 暖转人工与工单
  + 知识缺口回流
  + Agent 可观测（日志 · 成本 · 质量评估闭环）
  + 运营配置与审计
= 可试点、可自托管、可度量的企业智能客服底座
```

**不是什么：** 范围排除统一见 [§11.2](#112-明确不在范围)。

### 1.3 目标客户与场景

| 客户类型 | 典型场景 | 为何适合 |
|----------|----------|----------|
| 中小电商 / SaaS 售后 | 退换货、物流、账号、计费 FAQ | 知识可文档化；订单可 webhook 对接 |
| 内部 IT Helpdesk | 权限、VPN、报障、软件申请 | 工单 + 转人工；SOP 进知识库 |
| 产品技术支持 | API 用法、错误码、集成问题 | RAG + 引用；复杂单转人 |
| 自托管厂商交付 | 客户机房部署客服机器人 | 单租户、Compose、OpenAI 兼容模型 |

### 1.4 产品目标

| # | 目标 | 用户可感知结果 | 目标分期 |
|---|------|----------------|----------|
| G1 | 诚实 RAG | 有据可引；没把握就拒答并给弱证据 | MVP |
| G2 | 意图路由 | 同类问题走固定流程，不事事找大模型瞎聊 | MVP |
| G3 | 实时对话 | 流式输出、可取消、断线可续 | MVP |
| G4 | 工单 + 暖转人工 | 建单去重；转人有摘要队列；超时不黑洞 | MVP |
| G5 | 知识自进化 | 未答问题自动冒泡 → 审核入库 | MVP |
| G6 | 运营可配置 | 意图 / Prompt / 索引热更新 | MVP |
| G7 | 合规底座 | 审计、脱敏、生产密钥 fail-safe | MVP |
| G8 | 企业服务流程 | SLA 引擎、通知、SSO、技能组、连接器 | v2+ |
| G9 | Agent 编排闭环 | 多步规划/执行/工具失败恢复可观测；非仅单轮补全 | MVP 骨架 / v1.5 增强 |
| G10 | 多模型按需调度 | 分类/改写/生成/摘要可分模型；可降级与 fallback | MVP 配置 / v1.5 网关 |
| G11 | 成本可控 | 缓存命中、模型降级、单位会话成本可看板 | MVP 记账 / v1.5 优化 |
| G12 | 效果可预估可验证 | 上线前给预期指标，上线后对照 golden + 在线指标 | MVP 清单 / v1.5 自动化 |

### 1.5 设计原则

1. **证据优先于流畅**：宁可拒答，不编造政策 / 价格 / 订单状态。
2. **确定性护栏优先于 Prompt 软约束**：Harness、拒答阈值、路由白名单写在代码常量，不进运营模板。
3. **失败可降级、主流程不堵**：摘要失败仍转接；业务 webhook 失败可 mock/降级文案；缺口记录失败不影响聊天；工具调用失败进入恢复策略而非静默成功。
4. **配置热更新、契约冷更新**：意图路由与 Prompt 可热更；新增意图 / 路由 / 工具 / Loop 节点必须改代码 + 契约文档。
5. **单租户诚实**：不为伪多租户牺牲简单性；企业隔离靠独立部署实例。
6. **代码即契约**：Agent 行为以可执行契约（意图 / 路由 / 工具 / Harness / Handoff / Loop）为准，本 PRD 描述产品层语义。
7. **以 Agent 视角设计（Agent-native）**：设计时显式考虑规划边界、工具失败模式、上下文窗口物理上限；产物应让 Agent「如何解释与使用」清晰，而非只对人好看。
8. **方案可评估、可拍板**：任一关键问题至少列出 ≥2 条实现路径、权衡与推荐结论，避免「永远用最贵模型 / 永远上最重框架」。
9. **成本是一等公民**：prompt caching、批量/降级模型、短上下文优先不是可选优化，而是默认设计约束。
10. **自研 Loop 优先于重型编排器封装**：编排语义、护栏与可测性写在自有状态机/图中；框架（若引入）仅作适配层，不可成为行为黑盒。
11. **体验有质量门槛**：交互布局、间距、反馈动效达到「精致可用」下限（见 §4.19），代码评审可同时指出「逻辑错」与「观感廉价」。

### 1.6 成功标准

试点目标与统计口径统一见 [§9 业务指标](#9-业务指标)（核心：FAQ 自动解答率 ≥ 70%、检索准确率 ≥ 85%、👍 率 ≥ 80%、单位会话成本较基线 -20%）。

---

## 2. 用户角色与用户故事

### 2.1 角色矩阵

系统角色：`user`（外部用户）| `agent`（客服坐席）| `admin`（运营 / 知识 / 系统管理）。

| 能力域 | user | agent | admin |
|--------|:----:|:-----:|:-----:|
| 登录 / 聊天 / 自建工单 | ✅ | ✅ | ✅ |
| 对自己工单改状态（如关闭） | ✅ | ✅ | ✅ |
| 系统级工单列表 / 看板 | ❌ | ✅ | ✅ |
| 人工接管收件箱 | ❌ | ✅ | ✅ |
| 文档 / 意图 / Prompt / Gap / Draft | ❌ | 只读可选 | ✅ |
| 审计日志查询 | ❌ | 可选 | ✅ |
| 用户账号管理 | ❌ | ❌ | ✅（v1.5+） |

> MVP 可先让 agent 与 admin 共享运营后台门控；细粒度「只读知识」与完整用户管理 UI 可后置。

### 2.2 外部用户（user）

| ID | 用户故事 | 优先级 | 分期 |
|----|----------|--------|------|
| U-01 | 注册/登录后立即提问，无需安装插件 | P0 | MVP |
| U-02 | 答案带来源引用，方便核实 | P0 | MVP |
| U-03 | 无把握时明确拒答并建议换说法/转人工，不瞎编 | P0 | MVP |
| U-04 | 看到回答「靠谱程度」标识 | P1 | MVP |
| U-05 | 查订单忘了单号时，系统追问而不是直接失败 | P0 | MVP |
| U-06 | 说「转人工」后进入排队，收到客服真人回复 | P0 | MVP |
| U-07 | 转人工等待过久有反馈（超时升级工单 / AI 恢复） | P0 | MVP |
| U-08 | 对回答 👍 / 👎 | P1 | MVP |
| U-09 | 查看并关闭自己的工单 | P0 | MVP |
| U-10 | 上传截图报障 | P1 | v2 |
| U-11 | 访客（未登录）在官网挂件咨询 | P1 | v2 |
| U-12 | 用企业微信 / 飞书等同机器人 | P1 | v2 |

### 2.3 客服坐席（agent）

| ID | 用户故事 | 优先级 | 分期 |
|----|----------|--------|------|
| A-01 | 看到待接管队列，含摘要与最近对话 | P0 | MVP |
| A-02 | 认领会话；他人不可重复认领 | P0 | MVP |
| A-03 | 回复实时出现在用户聊天窗 | P0 | MVP |
| A-04 | 处理完可「交还 AI」或关闭会话 | P0 | MVP |
| A-05 | 按状态 / 优先级处理工单 | P0 | MVP |
| A-06 | SLA 将违约时主动提醒 | P0 | v2 |
| A-07 | 只收到本技能组队列 | P0 | v2 |
| A-08 | 写内部备注（用户不可见） | P1 | v2 |
| A-09 | 解决后可一键生成知识草稿 | P1 | MVP 能力 / v1.5 流程强化 |

### 2.4 运营 / 知识管理员（admin）

| ID | 用户故事 | 优先级 | 分期 |
|----|----------|--------|------|
| O-01 | 上传文档后可见 pending → indexing → active，大文件不卡死接口 | P0 | MVP |
| O-02 | 不发版即可改意图路由与 Prompt，并支持版本回滚 | P0 | MVP |
| O-03 | 自动看到机器人答不上的问题聚合列表 | P0 | MVP |
| O-04 | 审核草稿并发布进知识库 | P0 | MVP |
| O-05 | 看板看到 harness 拦截原因、👎 率、工单堆积 | P0 | MVP |
| O-06 | 谁删了文档、谁改了 Prompt 可审计 | P0 | MVP |
| O-07 | 发布知识后知道「重复问题是否下降」 | P1 | v2 |
| O-08 | 按业务线隔离 Bot / 知识范围 | P2 | 远期 |
| O-09 | 配置分级 SLA 与升级通知 | P0 | v2 |

### 2.5 系统管理员

| ID | 用户故事 | 优先级 | 分期 |
|----|----------|--------|------|
| S-01 | 默认弱密钥无法在生产启动 | P0 | MVP |
| S-02 | `/health` 报告各依赖状态 | P0 | MVP |
| S-03 | Prometheus 可抓业务指标 | P0 | MVP |
| S-04 | 有部署检查清单与 Runbook | P0 | MVP |
| S-05 | 对接公司 SSO | P0 | v2 |
| S-06 | 多副本无状态扩展无行为分叉 | P1 | v1.5 |
| S-07 | 按 purpose 切换模型并看到成本看板 | P0 | MVP 配置 / v1.5 网关 |
| S-08 | Agent run 可按 run_id 回放关键步骤与费用 | P0 | MVP |
| S-09 | 变更上线前填写效果预估，上线后自动或半自动对照 | P1 | v1.5 |

### 2.6 Agent 平台负责人（内部角色，非终端用户）

系统内可映射为 `admin` 或独立运维账号；用户故事强调 **Ownership**：

| ID | 用户故事 | 优先级 | 分期 |
|----|----------|--------|------|
| P-01 | 作为编排 Owner，我能定义/演进多步 Loop，而不是只能改一句 Prompt | P0 | MVP |
| P-02 | 我能为「分类 / 改写 / 生成 / 摘要 / 复杂推理」指定不同模型与降级链 | P0 | MVP |
| P-03 | 我能看到每次 run 的 token、费用估算、缓存命中与重试次数 | P0 | MVP |
| P-04 | 工具失败时有明确恢复策略（重试 / 换工具 / 澄清 / 转人工），且可测 | P0 | MVP |
| P-05 | 上线前我能给出预期指标，上线后用数据验证或回滚 | P0 | v1.5 |
| P-06 | 我能接入 MCP Server 扩展工具，而不改核心 Loop 骨架 | P1 | v1.5+ |
| P-07 | 高风险工具（代码执行 / 写文件）默认关闭或沙箱化 | P0 | v2（若启用） |

---

## 3. 系统架构

### 3.1 逻辑架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Clients: Web（用户工作台 + Admin）· 后续 Widget / 企业 IM        │
│  体验门槛：布局/间距/动效达到 §4.19 精致可用                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS REST + WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│  API 应用层                                                      │
│  Middleware: CORS · 限流 · 日志 · 异常 · metrics · cost 记账       │
│  ┌──────────┬──────────┬──────────┬──────────┬────────────────┐ │
│  │ Chat     │ RAG      │ Ticket   │ Handoff  │ Knowledge      │ │
│  │ Embedding│ Prompts  │ Admin    │ Audit    │ Health         │ │
│  └──────────┴──────────┴─────┬────┴──────────┴────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────▼────────────────────────────────┐ │
│  │  Agent Orchestration Layer（自研，Owner 全权负责）            │ │
│  │  Harness · Intent · Router · Multi-step Loop · Slot         │ │
│  │  Tool Registry（webhook / MCP / sandbox）                    │ │
│  │  Model Router（多模型调度 · fallback · 成本策略）             │ │
│  │  Context Manager（预算 · 缓存 · 长会话状态）                  │ │
│  │  Run Trace · Cost Ledger · Quality Eval hooks               │ │
│  └───────────────────────────┬────────────────────────────────┘ │
└──────────────────────────────┼──────────────────────────────────┘
                               │
        ┌──────────────────────┼────────────────────┐
        ▼                      ▼                    ▼
   PostgreSQL               Redis              向量库
   业务 / 审计 / 配置      会话 / 限流 / 队列     向量索引
   run 成本汇总            pub/sub / 缓存键          │
        │                      │                    │
        └──────────────────────┼────────────────────┘
                               ▼
                          对象存储
                          文档原文件
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              LLM 多厂商网关          MCP Servers
           (OpenAI 兼容 · 可选         （v1.5+）
            LiteLLM/OpenRouter 类）
```

### 3.2 单次用户消息处理流水线（产品语义）

```
WS 收 message
  → 鉴权 / 限流
  → 会话状态？
       transferred → 仅落库 + 通知坐席（不调 AI）
       active      → 进入 Agent 流水线
  → 用户消息落库
  → Harness.prepare（空/过长/注入/历史裁剪）
  → 槽位续跑判定（挂起工具入参，正则可优先于分类）
  → 意图分类（规则 + LLM）
  → 路由（运营配置 → 内置兜底 → 合法集）
  → Harness.choose_route（白名单 + 低置信改写）
  → ModelRouter.pick(purpose)   # classify | rewrite | generate | summary | …
  → 分支（可进入 Multi-step Loop，见 §4.13）：
       rag     → 改写 → 检索 → 证据评估 → (拒答 | 流式生成) → 引用自检 → 置信度
       tool    → Loop: 选工具 → 调参 → 执行 → 观察 → 恢复/再规划 → 可能挂起槽位
       ticket  → 创建工单（并发去重）
       handoff → 摘要 + 入队 + 会话转 transferred
       clarify → 澄清话术
  → Harness 输出约束（空输出兜底 / 超长截断）
  → CostLedger 记账（token · 模型 · 缓存命中 · 工具次数）
  → 助手消息落库
  → 知识缺口雷达（best-effort，失败不影响主流程）
  → WS 推送：token* · source · intent · ticket/handoff · message_end
```

### 3.3 技术选型建议

| 层 | 建议技术 | 选型理由 |
|----|----------|----------|
| API | FastAPI（或等价 async 框架）+ TypeScript/Python 之一为主 | 异步 + WebSocket + OpenAPI；生产级可独立交付 |
| Agent 编排 | **自研轻量状态图 / Loop**（非重型黑盒编排器） | 可控、可测、护栏可写死；可参考但不绑定 LangChain |
| 模型协议 | OpenAI 兼容（Chat Completions · **Function/Tool Calling** · **Structured Outputs**） | 生态主流；便于多厂商切换 |
| 多模型网关 | MVP：自研薄路由；v1.5+：可选 LiteLLM / OpenRouter 类 | 路由、fallback、统一计费字段 |
| ORM / 迁移 | SQLAlchemy 2 async + Alembic（若 Python） | 类型友好、标准迁移 |
| 向量 | ChromaDB（MVP）/ 可替换方案 | 轻量自托管；超大规模单独立项 |
| 关键词检索 | BM25（进程内或独立服务） | 混合检索必备 |
| 队列 / 推送 | Redis | 索引队列、限流、跨实例推送、prompt cache 键 |
| 对象存储 | MinIO / S3 兼容 | 文档原文件 |
| 前端 | React + Vite（动效可用 CSS / Framer Motion 级打磨） | 用户工作台 + Admin 一体；体验门槛 §4.19 |
| LLM / Embedding | 多厂商可配 | 按 purpose 选型与降级，见 §4.14 |
| 工具扩展 | 内置 Tool Registry + **MCP Client**（v1.5+） | 标准协议扩展；沙箱工具默认关 |

### 3.4 部署拓扑

| 环境 | 组成 |
|------|------|
| 本地开发 | Compose：PG、Redis、向量库、对象存储；本机 API + 前端 |
| 试点生产 | 单 worker API + TLS 反代；依赖与数据卷持久化 |
| 水平扩展 | 索引 / handoff 清扫须多 worker 安全；WS cancel 与 metrics 需有明确方案 |
| 企业目标 | SSO 反代、Prometheus + Alertmanager、备份任务、（可选）K8s |

### 3.5 Agent 编排层（Ownership）

**Owner 职责（产品强制声明）：** 编排层从方案选型 → 架构 → 开发 → 上线 → 效果复盘 **有明确负责人**，对应能力不外包给「随便包个框架」。

| 子系统 | 职责 | 失败时 |
|--------|------|--------|
| Cognitive Harness | 输入/路由/输出硬约束 | 硬停或强制兜底路由 |
| Intent + Router | 分类与节点选择 | clarify / rag 兜底 |
| **Multi-step Loop** | plan → act → observe → recover | 达最大步数 → 澄清或 handoff |
| Tool Registry | 工具描述、权限、超时、幂等键 | 按错误类重试/降级/转人工 |
| Model Router | purpose → 模型链、温度、结构化输出 | 链上下一个模型或固定话术 |
| Context Manager | 历史裁剪、证据组装、缓存键 | 缩上下文优先于硬失败 |
| Cost Ledger | token/费用/缓存命中 | 记账失败不挡主路径 |
| Eval Hooks | 离线 golden / 在线采样 | 不阻塞实时会话 |

**能力边界（设计评审必须显式覆盖）：** Loop 步数与工具白名单上限（§4.13.3）、工具失败模式与非幂等副作用（§4.13.4）、上下文窗口物理上限（§4.15）、厂商在结构化输出 / 工具调用 / 长上下文 / 价格上的差异（§4.14.4）；禁止开放式「无限自主」。

**方案权衡模板（任一重大选型必填，附录 E）：** 问题 → ≥2 路径 → 成本/质量/复杂度/风险 → 推荐与否决原因。

---

## 4. 功能需求

### 4.1 认证与账号

| 功能 | 行为要求 |
|------|----------|
| 注册 | username / email / password；默认 role=`user` |
| 登录 | 返回 JWT（或等价会话令牌） |
| 当前用户 | Bearer 鉴权解析 |
| 密码 | 安全哈希存储 |
| 生产密钥 | 默认 secret + 非 development 环境 → **拒绝启动** |
| 限流 | 按用户/IP 分钟级限流（默认建议 60/min，可配） |
| 角色门控 | 前端路由 + 后端依赖双重校验 |

**验收要点：**

- 错误密码不可登录；过期 token 被拒绝
- 生产不把 JWT 放进 WebSocket URL
- 无有效 token 不可访问业务页面与 API

**v2 扩展：** SSO（OIDC/SAML）、JIT 开通、角色映射、服务账号 API Key、用户管理 UI。

---

### 4.2 智能问答（Honest RAG）

#### 4.2.1 检索与生成

| 步骤 | 要求 |
|------|------|
| 历史上下文 | 按 §4.15.1 预算裁剪后进入模型 |
| BM25 召回 | 关键词通道 |
| 向量召回 | 语义通道；chunk 元数据含 source / generation / indexed_at |
| 融合 / 可选 rerank | 融合通道；rerank 为可插拔 hook |
| 过滤 | 支持按 sources / doc_ids / 时间窗过滤；tags 可预留 |
| Grounding 评估 | 按通道归一化置信度；低于阈值则拒答 |
| 弱证据拒答 | **不调 LLM**；固定文案 + 最多 N 条弱来源 |
| Prompt 组装 | 运营模板优先，代码常量兜底 |
| 流式生成 | token 帧；总输出超上限则截断并提示 |
| 行内引用 | 答案中 `[n]` 与 sources[].index 对齐 |
| 证据自检 | 超时/失败可跳过并打标；越界引用打标 |
| 回答置信度 | 随 message_end 下发，前端 badge 展示 |
| 故障话术 | 无结果 / LLM 宕机分模板 |

#### 4.2.2 Grounding 默认旋钮（可调，须配合 eval）

| 参数 | 建议默认 | 含义 |
|------|----------|------|
| 证据置信度阈值 | 0.35 | 低于则拒答 |
| 最少命中数 | 1 | 零命中无条件拒答 |
| 拒答仍展示来源数 | 2 | 引导换问法 / 转人工 |

#### 4.2.3 离线评估

- 维护 golden 语料与拒答用例
- 覆盖：FAQ 命中、引用有效性、拒答行为
- 目标：接入 CI 门禁（v1.5+）

#### 4.2.4 用户可见 UX

- 流式打字效果
- 来源列表 / 引用高亮
- 置信度 badge
- 拒答时仍可展示弱来源

---

### 4.3 意图识别与路由

#### 4.3.1 意图清单（MVP）

| Intent | 含义 | 规则命中特征（示意） | 默认路由 |
|--------|------|----------------------|----------|
| `faq` | 通用知识问答（默认） | 无关键词规则，LLM 兜底 | rag |
| `product` | 产品功能 | LLM | rag |
| `order_query` | 订单 / 物流 / 发货 | 订单、快递、物流、发货、order、shipping… | tool |
| `fault_report` | 故障 / Bug | 报错、错误、bug、500、故障、crash… | ticket |
| `complaint` | 投诉 / 不满 | 投诉、差评、不满、complain… | ticket |
| `handoff` | 转人工 | 须「真人/人工/客服」类词与「转/找/talk」类词**共现** | handoff |

**分类策略：**

1. 规则命中 → 中等置信度（如 0.7）
2. LLM 二次判断 JSON `{intent, confidence}`；与规则比高者胜
3. LLM 置信度过低 → 需要澄清
4. LLM 失败 → 规则结果，或 `faq` + 低置信 + 澄清
5. `handoff` **禁止**仅因出现 “agent” 等词误触发

**v1.5+ 建议新增：** `out_of_scope`（域外问题拒答，避免强塞进 FAQ 导致幻觉）。

#### 4.3.2 路由决策顺序

```
1. 无 intent                              → rag
2. 需要澄清且置信度过低                   → clarify
3. 运营配置的 intent → route 映射         → 热更新
4. 内置兜底路由表
5. 非法 target                            → rag + 告警
6. Harness 二次校验：
     - 不在白名单 → rag
     - 置信度过低 → clarify
```

合法路由集：`{rag, ticket, handoff, clarify, tool}`。

配置缓存须支持 TTL + 跨实例失效广播，并避免「加载中收到失效又把旧值写回」的竞态。

#### 4.3.3 Cognitive Harness

| 阶段 | 条件 | 动作 |
|------|------|------|
| prepare | 空问题 | 停止 + 固定话术 |
| prepare | 超长问题（如 >2000 字） | 停止 |
| prepare | Prompt 注入 / 控制类请求 | 停止（安全文案**不可**运营改） |
| prepare | 历史过长 / 单条过长 | 裁剪 / 截断 + 打标 |
| prepare | 历史角色非法 | 丢弃（人工消息若入历史须镜像为 assistant） |
| choose_route | 非法路由 / 低置信 | 强制兜底 |
| finalize / stream | 空输出 | 兜底话术 |
| finalize / stream | 超长输出 | 截断 + 提示 |

每次决策写入可追踪 trace（run_id、policy_version、flags、reason、route、retrieval_* 等），供运营看板与知识缺口雷达消费。Harness 安全文案与阈值不进 Prompt 模板（禁入清单见 §4.10.2）。

---

### 4.4 工具调用与槽位填充

#### 4.4.1 工具（MVP）

| 工具名 | 触发意图 | 入参 | 成功要点 | 失败策略 |
|--------|----------|------|----------|----------|
| `search_order` | order_query | order_id（正则抽取） | status / tracking / ETA / data_source | 未配置 → mock；超时/HTTP 失败 → mock + 原因 + 指标 |
| `search_knowledge` | 可运营配置的检索意图 | query, top_k | 标题 / 来源 / 内容 / 分数 | 异常 → 空列表 |

#### 4.4.2 槽位状态机（以订单号为例）

会话 metadata 中挂起：

```json
{
  "tool": "search_order",
  "slot": "order_id",
  "intent": "order_query",
  "turns_waited": 0
}
```

| 用户下一句 | 系统行为 |
|------------|----------|
| 命中订单号 | **续跑**：跳过分类，高置信走 tool；成功清档 |
| 未命中 + 同意图 | 继续追问；超过最大轮次（建议 3）→ 清档转澄清 |
| 未命中 + 异意图且高置信 | **弃槽**，按新意图路由（如 handoff） |
| 未命中 + 异意图低置信 | 保留槽位，正常路由 |

持久化须 merge-patch，禁止整表覆盖 metadata。

#### 4.4.3 扩展新工具约定

1. 注册工具 handler
2. 映射 intent → tool
3. 需要多轮入参则扩展槽位决策表
4. 同步 Agent 行为契约文档
5. webhook / 密钥走配置，禁止写死

---

### 4.5 聊天与会话

#### 4.5.1 会话生命周期

| 操作 | 能力 |
|------|------|
| 创建 / 列表 / 重命名 / 归档 / 删除 | REST |
| 拉取历史消息 | REST |
| 实时对话 | WebSocket |
| 反馈 👍 / 👎 / 中性 + 评论 | REST upsert |

会话状态：

| 状态 | 含义 |
|------|------|
| `active` | AI 正常应答 |
| `transferred` | 人工接管中，用户消息**不进 AI** |
| `closed` | 结束 |

#### 4.5.2 WebSocket 协议（产品级）

**连接：** 先连接后首帧 `auth` 带令牌（超时未认证关闭）。

**客户端 → 服务端：**

| type | 用途 |
|------|------|
| `auth` | 鉴权 |
| `message` | 用户发言 |
| `cancel` | 取消生成 |
| `ping` | 心跳 |

**服务端 → 客户端：**

| type | 用途 |
|------|------|
| `token` | 流式片段 |
| `intent` | 分类结果 |
| `source` | 检索来源 |
| `ticket` | 工单创建/更新 |
| `handoff` | 转接开始 |
| `staff_message` | 客服回复 |
| `handoff_update` | 接管状态变化 |
| `message_end` | 一轮结束（含 message_id、sources、verification、answer_confidence） |
| `error` | 错误 |
| `pong` | 心跳回应 |

#### 4.5.3 前端页面（用户）

- 会话列表、消息流、输入框、信息侧栏
- 建单对话框、转人工横幅、staff 气泡
- 我的工单列表与详情

---

### 4.6 工单系统

#### 4.6.1 字段与状态

| 字段 | 说明 |
|------|------|
| type | fault_report / complaint / handoff_timeout / 用户自建类型等 |
| status | pending → processing → resolved / closed |
| priority | low / medium / high / urgent |
| title / description | 文本 |
| assignee | 坐席标识（MVP 可为字符串；v2 关联用户/技能组） |
| content | JSON 扩展 |
| conversation_id | 可空关联 |
| resolved_at | 进入 resolved 时写入 |

#### 4.6.2 创建路径

1. Agent 路由：fault_report / complaint → 高优自动建单
2. 用户自建：聊天侧 / REST
3. Handoff 超时：类型 `handoff_timeout`、高优

**去重正确性（实现红线）：** 同一用户 + 同一标题在「未关闭/未解决」状态下唯一；并发创建必须收敛到同一条开放工单。

#### 4.6.3 权限

| 角色 | 可做 |
|------|------|
| user | 建单、看自己的、关闭自己的 |
| agent / admin | 系统列表、改 status / assignee / priority、看板 |

#### 4.6.4 看板（MVP）

- 各状态计数
- 开放单是否超过统一 SLA 阈值（如 24h）的事后统计
- 按优先级分布、最老开放单年龄
- 近 7 日 created vs resolved

**v2：** 分级 SLA、定时扫描、自动升级、离线通知（见 §10 Wave A）。

#### 4.6.5 通知（MVP）

在线用户经 WebSocket 推 ticket 帧。离线通知见 v2 通知中心。

---

### 4.7 人工接管（Handoff）

#### 4.7.1 设计意图

Handoff 与 Ticket **分表**：

| 概念 | 职责 |
|------|------|
| Handoff | **实时认领会话**（queued / claimed / 回流） |
| Ticket | **异步工作项**（可跨天解决） |
| 超时 handoff | **派生**高优工单，避免「无人也无 AI」 |

#### 4.7.2 状态机

```
                    claim
        queued ──────────► claimed
          │                   │
          │ timeout           │ resolve(returned)
          │                   ├──────────► returned  → 会话 active（AI）
          │                   │ resolve(resolved)
          ▼                   └──────────► resolved → 会话 active 或 closed
       timed_out
       (+ 建 handoff_timeout 工单
        + 会话回 active)
```

约束：每个 conversation 最多一条 open（queued | claimed）session。

#### 4.7.3 入队载荷

```json
{
  "recent_messages": [{"role": "...", "content": "...", "created_at": "..."}],
  "intent_history": ["faq", "handoff"],
  "user_meta": {"user_id": "...", "session_start_at": "..."},
  "ticket_refs": ["..."],
  "flags": ["summary_failed"]
}
```

- 最近消息：从 durable 消息存储取最近 N 条（建议 10）
- 摘要：同步生成但硬超时（建议 8s）；失败则空摘要 + flag，**转接不阻塞**

#### 4.7.4 坐席操作

| 操作 | 行为 |
|------|------|
| 列表 | 按 status 过滤分页 |
| 详情 | session + 全量消息 |
| claim | 条件更新；冲突返回 409 |
| reply | 仅 assignee；消息角色 staff，但会话镜像须让 AI 暖回流后可见 |
| resolve | resolved / returned；可选关闭会话 |

#### 4.7.5 超时清扫

- 周期性扫描（建议 60s）
- 超时阈值可配（建议默认 10 分钟）
- 动作：建高优工单 → 标 timed_out → 会话回 active → 推送用户 → 指标 +1
- 多实例须防重复升级（如 `SKIP LOCKED`）

---

### 4.8 知识库与异步索引

#### 4.8.1 文档状态机

```
upload → pending → (worker claim) → indexing → active
                              ↘ failed（错误可查）
active → archived（删除 / 下线）
```

#### 4.8.2 索引管道

1. 上传：写元数据 pending + 原文件入对象存储 + **入队**（HTTP 不阻塞 embedding）
2. Worker 消费：条件 claim 防双消费
3. parse → chunk（建议 size=500, overlap=50）→ embed → 写向量库
4. **先写新 generation 再删旧**，失败不造成检索黑洞
5. 刷新关键词索引
6. 成功 active / 失败 failed
7. 启动时 orphan 重排（卡住的 indexing / pending）

支持 reindex（原文件仍在对象存储）。

#### 4.8.3 格式

- **MVP：** PDF / Markdown / TXT
- **后续：** docx / html / 网页抓取、预览下载 API

#### 4.8.4 运维约定

- 更换 embedding 模型 / 维度 → **全量 reindex**
- 启用元数据过滤前，旧 chunk 须具备完整 metadata
- 须具备（或规划）业务库 / 向量库 / 对象存储三方对账手段

---

### 4.9 知识自进化（Knowledge Loop）

#### 4.9.1 缺口雷达信号

被动消费 harness / 反馈信号，**不改路由**：

| 信号类型 | 来源示意 |
|----------|----------|
| clarify | 路由到澄清 |
| rag_refusal | 命中拒答话术 |
| low_retrieval_score | 检索置信度低 |
| handoff | 转人工 |
| negative_feedback | 用户 👎 |

捕获全程 best-effort；失败只记内部错误，不回抛聊天。

#### 4.9.2 Gap 实体

- 按 question_hash 对 open 状态聚合（partial unique）
- frequency 累加；signals 计数
- 保留 example conversation / message
- 状态：open → promoted | dismissed

#### 4.9.3 Draft 流程

```
Gap --create draft--> KnowledgeDraft(draft)
        │
        ├ edit (question / answer)
        ├ reject (+ review_note)
        └ approve → 创建 Document → 索引管线 → published
                     回填 gap.promoted_doc_id
```

每个 gap 最多一条 pending 草稿。

**v2 增强：** 发布后效果归因、灰度发布、关单强制沉淀 SOP。

---

### 4.10 运营配置：意图与 Prompt

#### 4.10.1 意图配置

Admin CRUD：name、route_target、启用等。变更后本地缓存失效 + 跨实例广播。

#### 4.10.2 Prompt 模板（MVP Key）

| Key | 用途 | 约束 |
|-----|------|------|
| `rag.system` | RAG 系统提示 | 声明变量 |
| `rag.context` | 上下文拼装 | 如 chunks / question |
| `rag.fallback_no_results` | 无结果 | — |
| `rag.fallback_llm_down` | LLM 故障 | — |
| `intent.classifier` | 意图分类 | **必须**保留消息占位符与意图标签集合 |
| `agent.clarify` | 澄清话术 | — |

版本语义：

- 版本**只追加**
- 切换 active 指针 = 发布 / 回滚
- 内容长度上限与占位符渲染校验
- 读路径：DB 优先，失败回落代码常量

**禁止进模板：** Harness 安全拒答、截断提示、通用 fallback_response 等。

---

### 4.11 审计与脱敏

#### 4.11.1 审计日志

| 字段 | 含义 |
|------|------|
| actor_id / actor_role | 谁 |
| action | 动作名 |
| entity_type / entity_id | 对象 |
| detail | JSON，**写入前脱敏** |
| trace_id | 关联请求日志 |
| created_at | 仅追加，无 update |

与业务变更**同事务**：业务回滚则审计不留幽灵记录。

#### 4.11.2 脱敏

| 模式 | 建议默认 | 行为 |
|------|----------|------|
| 日志 | 开启 | 渲染前递归 mask |
| 落库消息 | 关闭 | 开启则强隐私、弱 handoff 上下文质量 |

MVP 覆盖：手机号、邮箱、订单号部分遮罩。  
v2：身份证 / 银行卡 / 地址、字段级策略、SIEM 导出。

---

### 4.12 管理分析与系统健康

#### 4.12.1 Analytics

- 量：conversations / messages / tickets / documents
- intent 分布、平均意图置信度
- harness fallback / truncate 率及 reason / flag 分布
- 近 7 日 👎 率与反馈量

**运营用法示例：**

- `prompt_control_request` 突增 → 注入探测
- `response_truncated` 突增 → 输出预算过紧或模型啰嗦
- `weak_retrieval_refusal` + gap frequency → 知识缺口
- 👎 率升 → 回看文档与 Prompt 版本

#### 4.12.2 System Health

- 依赖探活：PG / Redis / 向量库 / 对象存储
- 文档状态计数、最老 pending 年龄、chunk 总数、last_indexed_at
- 24h 审计 action 分布
- 应用版本 / harness 策略版本

#### 4.12.3 Admin 页面地图

| 页面 | 功能 |
|------|------|
| Dashboard | 总览 + 系统健康 |
| Tickets / Ticket Dashboard | 工单与 SLA 统计 |
| Documents | 文档与索引 |
| Intents | 意图路由 |
| Prompts | 提示词版本 |
| Gaps | 知识缺口 |
| Knowledge | 草稿审核 |
| Handoffs | 接管收件箱 |
| **Models / Cost**（v1.1） | 模型路由配置、单位成本、缓存命中 |
| **Agent Runs**（v1.5） | 按 run_id 回放步骤 / 工具 / 费用 |
| **Launch Cards**（v1.5） | 上线预期 vs 实测效果卡片 |

---

### 4.13 Agent 编排闭环（Multi-step Loop）

> 对应 Ownership：从单轮补全升级为 **规划 → 执行 → 观察 → 纠错 → 结束** 的可测闭环。

#### 4.13.1 何时进入 Loop

| 路由 | Loop 形态 | 说明 |
|------|-----------|------|
| `rag` | 短环（0–1 步工具可选） | 改写→检索→生成；一般不开放任意工具 |
| `tool` | **标准多步环** | 槽位补齐 + Function Calling + 恢复 |
| `ticket` / `handoff` / `clarify` | 零或一步 | 确定性业务动作，避免模型乱规划 |
| 复合场景（v1.5+） | 受控多步 | 如「查单失败 → 建单 → 告知」须白名单剧本 |

#### 4.13.2 Loop 状态机（产品语义）

```
                    ┌──────────────┐
                    │    PLAN      │  选下一步：tool / answer / clarify / handoff / stop
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
              ┌────►│    ACT       │  模型 structured call 或确定性节点
              │     └──────┬───────┘
              │            ▼
              │     ┌──────────────┐
              │     │   OBSERVE    │  工具结果 / 检索证据 / 错误类
              │     └──────┬───────┘
              │            ▼
              │     ┌──────────────┐
              │     │   RECOVER    │  重试 · 换参 · 换工具 · 降级 · 升级人工
              │     └──────┬───────┘
              │            │
              └─ 未完成且未超预算 ─┘
                           ▼
                    ┌──────────────┐
                    │  FINALIZE    │  Harness 输出约束 · 记账 · 落库
                    └──────────────┘
```

#### 4.13.3 硬预算（物理上限）

| 预算 | 建议默认 | 超限行为 |
|------|----------|----------|
| `LOOP_MAX_STEPS` | 6 | 停止 → 澄清或 handoff（可配） |
| `LOOP_MAX_TOOL_CALLS` | 4 | 同上 |
| `LOOP_MAX_WALL_MS` | 45000 | 取消未完成工具 · 降级话术 |
| `LOOP_MAX_RETRIES_PER_TOOL` | 2 | 按错误类（超时可重试；4xx 参数错不重试） |

#### 4.13.4 工具调用失败模式（设计必覆盖）

| 失败类 | 示例 | 恢复策略 |
|--------|------|----------|
| 超时 | webhook > N 秒 | 有限重试 → mock/降级 → 说明原因 |
| 参数非法 | 缺 order_id | 槽位追问；不盲重试 |
| 下游 5xx | 订单中心故障 | 重试 + 熔断；UI 标明 data_source |
| 权限/未配置 | 无 webhook | mock + 指标；禁止假装真实数据 |
| 非幂等重复 | 重复建单 | 业务层去重（已有 ticket 红线） |
| 模型乱调工具 | 不在白名单 | Harness 拒绝 · 记 flag · 不执行 |

#### 4.13.5 与 OpenAI 生态的产品约定

| 能力 | 用途 | 约束 |
|------|------|------|
| Tool / Function Calling | 工具选择与参数 | 仅 Registry 内工具；JSON schema 校验 |
| Structured Outputs | 意图 JSON、计划步、槽位 | 解析失败 → 规则回落，不崩主路径 |
|（不绑定）Assistants API | 可选适配 | **行为真相以自研 Loop 为准**，禁止双脑并行 |

#### 4.13.6 验收要点

- 工具超时路径可单测：必走到恢复策略且用户可见合理解释  
- 超过 `LOOP_MAX_STEPS` 不会死循环  
- run trace 含每步 tool name、latency、error_class、retry  
- 未授权工具调用次数 = 0  

---

### 4.14 多模型路由与调度

#### 4.14.1 设计目标

- **按场景选模型**，能说清「为什么这个任务用这个模型」，而不是默认最贵。  
- **质量下限 + 成本上限** 同时可配置。  
- 厂商可替换：OpenAI 兼容优先；可配 Claude / Gemini / DeepSeek / Qwen / 本地 Ollama 等。

#### 4.14.2 Purpose（调用目的）矩阵

| purpose | 质量敏感度 | 延迟敏感 | 建议档位（示例，可配） | 说明 |
|---------|------------|----------|----------------------|------|
| `intent_classify` | 中 | 高 | 小/中模型 + Structured Outputs | 可规则优先，LLM 兜底 |
| `query_rewrite` | 中 | 高 | 小模型或规则（默认规则） | 失败回落原文 |
| `rag_generate` | **高** | 中 | 中大模型；弱证据时 **不调用** | 诚实回答主路径 |
| `handoff_summary` | 中 | 高 | 小/中模型；硬超时 | 失败空摘要不阻塞 |
| `gap_draft_assist` | 中 | 低 | 中模型 | 运营侧，可异步 |
| `complex_reason`（可选） | 高 | 低 | 大模型 / 扩展思考（若厂商支持） | 默认关；仅白名单意图 |
| `embedding` | — | 中 | 专用 embedding 模型 | 与 chat 模型分离 |

#### 4.14.3 路由策略

```
1. 读取 purpose 的 primary 模型
2. 健康检查 / 熔断开启？ → 走 fallback 链
3. 成本熔断（日预算将尽）→ 强制降级链
4. 超时 / 5xx / 内容过滤 → 下一候选
5. 链耗尽 → 确定性话术或规则路径（classify→规则，generate→fallback 模板）
```

配置形态（逻辑）：

```yaml
models:
  intent_classify:
    primary: { provider: openai_compat, model: "qwen-plus", timeout_ms: 2000 }
    fallback: [{ model: "deepseek-chat" }, { model: "gpt-4o-mini" }]
  rag_generate:
    primary: { provider: openai_compat, model: "gpt-4o", timeout_ms: 60000 }
    fallback: [{ model: "claude-sonnet" }, { model: "deepseek-chat" }]
```

#### 4.14.4 模型能力画像（选型时必参考，非排名广告）

| 维度 | 选型问题 |
|------|----------|
| 工具调用稳定性 | 是否经常编造参数 / 忽略 schema？ |
| 结构化输出 | JSON 服从率是否够意图分类？ |
| 长上下文 | 是否真能用满，还是中段遗忘？ |
| 中文客服语气 | 政策拒答是否稳健？ |
| 价格与限速 | RPM/TPM、缓存折扣、批量 API |
| 数据驻留 | 私有化是否只允许本地/专有云？ |

**产品文案要求：** Admin 或运维文档中每个 purpose 旁展示「选用理由」字段（一句话），避免黑盒默认。

#### 4.14.5 验收要点

- 同一请求可配置切换 `rag_generate` 模型而不改业务代码  
- fallback 触发可在 metrics 中按 `provider/model/reason` 观察  
- 关闭大模型后 classify 仍可走规则路径  

---

### 4.15 Prompt 工程与上下文预算（含缓存）

#### 4.15.1 Token 预算（默认）

| 预算项 | 建议默认 | 说明 |
|--------|----------|------|
| 历史消息条数 | 12 | 超限丢最旧 |
| 单条消息字符 | ~1200 | 截断 + flag |
| 检索 chunk 数 | 6 | 进生成上下文 |
| 单 chunk 字符 | ~800 | |
| 生成 max tokens | 按模型档 | 超限 Harness 截断 |
| 分类 / 改写 max tokens | 小（如 64–256） | 防废话 |

#### 4.15.2 长会话状态

| 机制 | MVP | v1.5+ |
|------|-----|-------|
| 滑动窗口裁剪 | ✅ | ✅ |
| 槽位 metadata merge-patch | ✅ | ✅ |
| staff→assistant 镜像 | ✅ | ✅ |
| 中段会话摘要压缩 | — | ✅（摘要模型走 Model Router） |
| 用户长期记忆 | ❌ 默认不做 | 需独立隐私评审 |

#### 4.15.3 Prompt Caching 策略

| 层级 | 策略 | 分期 |
|------|------|------|
| 前缀稳定段 | `rag.system` 等尽量前缀不变，利于厂商 prompt cache | MVP 约定 |
| 应用侧结果缓存 | 同 `question_hash + doc_generation` 短 TTL 检索结果缓存（可选） | v1.5 |
| 语义缓存 | 近似问句复用回答 | **默认关**（政策时效风险高） |
| 嵌入缓存 | 相同文本 embedding 去重 | MVP 建议 |

配置：`PROMPT_CACHE_ENABLED`、`RETRIEVAL_CACHE_TTL_S`；命中必须打 metrics `cache_hit`。

#### 4.15.4 验收要点

- 超长历史不导致上下文溢出错误（有裁剪）  
- 缓存命中时费用字段可区分  
- 运营改 system prompt 后缓存键/前缀策略有文档说明  

---

### 4.16 工具链：MCP · 沙箱 · 文件系统

#### 4.16.1 Tool Registry（MVP 必有）

| 字段 | 说明 |
|------|------|
| name / description / JSON schema | 给模型与校验器 |
| permission | 角色 / 是否允许 LLM 自选 |
| timeout / retry_policy | |
| side_effect | `read` / `write` / `money` 等标签 |
| impl | webhook / 内置 / MCP / sandbox |

**MVP 内置：** `search_order`、`search_knowledge`（及确定性 ticket/handoff 节点）。

#### 4.16.2 MCP（Model Context Protocol）

| 项 | 要求 |
|----|------|
| 分期 | **v1.5+** 作为扩展工具来源 |
| 角色 | AskFlow 作 **MCP Client** 连接外部 MCP Server |
| 安全 | 工具白名单导入；默认只读；变更类工具需 admin 显式启用 |
| 契约 | MCP 工具进入同一 Registry 与 Loop，不另起编排脑 |

#### 4.16.3 代码执行沙箱 / 文件系统

| 能力 | 默认 | 说明 |
|------|------|------|
| 代码执行沙箱 | **关** | 客服主场景非必须；开启需隔离网络与资源配额 |
| 任意文件系统写 | **关** | 仅对象存储文档管道可写 |
| 受控读知识原文件 | 管理端 | 预览/下载走鉴权 API |

**原则：** 不为了「Agent 很强」默认打开高危工具；Helpdesk 排障若需要，走独立 Wave 与威胁建模。

#### 4.16.4 验收要点

- Registry 外工具无法被模型执行  
- MCP 未配置时系统功能完整（降级为内置工具）  
- 沙箱默认关闭的启动测试  

---

### 4.17 Agent 可观测、成本与质量闭环

#### 4.17.1 日志与 Run 回放

| 字段 | 必须 |
|------|------|
| `trace_id` / `run_id` | ✅ |
| purpose → model → provider | ✅ |
| loop step / tool / error_class / retry | ✅ |
| token prompt/completion、cache_hit | ✅ |
| 估算费用（USD 或本地币，按价目表） | ✅（可近似） |
| flags / route / intent / grounding | ✅ |

PII 脱敏规则同 §4.11。

#### 4.17.2 成本看板（Admin）

| 视图 | 内容 |
|------|------|
| 总览 | 日/周费用、单位会话成本、分 purpose 占比 |
| 模型 | 各 model 调用量、错误率、fallback 率 |
| 缓存 | prompt/检索缓存命中率 |
| 异常 | 单会话费用 Top N（排障贵请求） |

#### 4.17.3 质量评估闭环

```
离线 golden / refusals
  → 发布前跑（MVP 手工/脚本；v1.5 CI 门禁）
在线：👍👎 · 拒答率 · handoff 率 · 工具成功率
  → Dashboard + 告警
Gap 雷达
  → Draft → 发布 → 再 eval
```

**禁止**用「解答率」单指标优化到牺牲拒答诚实性（PRD 红线延续）。

#### 4.17.4 验收要点

- 任意成功对话可查到费用估算与模型名  
- LLM 错误与 fallback 有 Prometheus 计数  
- 质量指标与成本指标可同屏对比（防「降本降质」无感）  

---

### 4.18 上线前效果预估与上线后验证

#### 4.18.1 适用变更类型

涉及以下之一的发布，**必须**附「效果卡片」（Launch Card）：

- Prompt 模板激活 / 回滚  
- 模型路由 primary/fallback 变更  
- Grounding 阈值、Loop 预算、改写策略  
- 新工具 / MCP 工具启用  
- 意图路由映射大改  

#### 4.18.2 卡片字段（上线前）

| 字段 | 说明 |
|------|------|
| 变更摘要 | 一句话 |
| 预期影响指标 | 如拒答率 ±x pp、TTFT、单位成本、👍 率 |
| 预期风险 | 如分类漂移、成本上升 |
| 回滚方式 | activate 旧 Prompt / 配回旧模型 |
| 离线 eval 结果 | golden 通过率前后对比 |
| 观察窗口 | 建议 24–72h |

#### 4.18.3 上线后验证

| 动作 | 说明 |
|------|------|
| 自动抓取窗口内核心指标 | 与预期对比 |
| 结论 | 达标 / 观察 / **回滚建议** |
| 留存 | 卡片进审计或 Admin 历史，供复盘 |

MVP：Markdown/表格模板 + 人工填写；v1.5：Admin 表单 + 指标自动回填。

#### 4.18.4 验收要点

- 模板与示例进 `deploy/checklists` 或 Admin  
- 至少一次试点发布完整走过「预估 → 上线 → 对照」  

---

### 4.19 交互体验质量门槛（UX Bar）

> 来自工程文化：不要求人人是设计师，但必须能区分「精致」与「廉价」。

#### 4.19.1 适用范围

用户工作台、转人工横幅、来源引用、置信度 badge、Admin 核心表单与空状态。

#### 4.19.2 最低标准（即 UX 走查清单，供 §10.1 / §12.1 走查引用）

| 维度 | 要求 |
|------|------|
| 布局 | 对齐、间距节奏一致；避免元素贴边/重叠；转人工横幅与 staff 气泡层级清晰 |
| 反馈 | 流式输出、取消、加载、错误、限流有明确状态，不「假死」 |
| 动效 | 可选用 CSS 过渡；避免刺眼闪烁；尊重 `prefers-reduced-motion` |
| 信息层次 | 引用、置信度、data_source=mock 等关键信息不淹没在正文 |
| 错误与空状态 | 有可读文案，非原始堆栈 |
| 无障碍基础 | 可键盘聚焦主输入；对比度不过低 |
| 评审权 | CR 可因「观感不达标」要求修改，等同于逻辑缺陷的阻断级（P1 路径） |

#### 4.19.3 非目标

- 不追求营销站级品牌动效  
- 不强制统一设计系统一期上齐（可渐进）  

---

## 5. 端到端业务旅程

### 5.1 旅程 A：知识问答（幸福路径）

```
用户登录 → 选/建会话 → 「退货政策是什么？」
  → harness ok → intent=faq
  → rag 检索命中政策 chunk
  → grounding 通过
  → 流式回答 + [1][2] 引用
  → message_end(message_id, verification, answer_confidence)
  → 用户 👍
```

**失败分支：**

- 检索弱 → 拒答 + 弱来源 + gap 信号
- LLM 超时 → fallback 话术
- 用户 👎 → 反馈 + 可进缺口分析

### 5.2 旅程 B：订单查询（槽位 + Loop 失败恢复）

```
「帮我查物流」→ order_query → enter Loop
  → PLAN: need search_order · missing order_id → ACT: 追问 + 挂起 pending_tool
「AB12345678」→ 正则续跑（跳过分类）→ ACT: search_order
  → OBSERVE 成功 → 展示状态（含 data_source）
```

**失败分支：**

- webhook 超时 → RECOVER：重试 1 次仍失败 → mock 降级 + 标明 data_source + 指标 → FINALIZE 解释「查询通道异常，以下为降级信息/建议转人工」→ CostLedger 入账（classify +（可选）rewrite + tool）
- 用户中途改口「转人工」→ 弃槽改走 handoff（§4.4.2）

### 5.3 旅程 C：故障报修 → 工单

```
「后台 500 了」→ fault_report → ticket(high)
  → 去重：同标题 open 单则返回已有
  → ticket 帧通知用户
  → 坐席看板处理 → resolved
  → （目标）从 ticket 生成 draft → 审核 → 入库
```

### 5.4 旅程 D：暖转人工

```
「我要找真人」→ handoff
  → 摘要(≤超时) + payload 入队 → conversation=transferred
  → 用户见排队横幅
  → 坐席 claim → 实时 reply
  → 用户继续发消息：只落库+推坐席，不进 AI
  → resolve(returned) → active，AI 带着人工历史继续
或 超时无人 claim → timed_out + 高优工单 + AI 恢复
```

### 5.5 旅程 E：知识运营日课

```
早会：Gaps 页按 frequency 排序
  → 选高频 gap → 生成 draft
  → 编辑标准答 → approve → 文档 active
  → 跑离线 eval 回归
  → Dashboard 看拒答率与 👎 是否下降
```

### 5.6 旅程 F：紧急改话术

```
发现分类不准 → 编辑 intent.classifier
  → 新版本 → activate → 缓存失效
  → 新会话立即用新 prompt（无需发版）
  → 审计留下 actor + 版本
  → 若更差 → activate 旧 version 回滚
```

### 5.7 旅程 G：模型降级与成本（v1.1）

```
高峰 / 日预算告警 → ModelRouter 将 rag_generate 切到 fallback 中档模型
  → Dashboard：单位成本下降、拒答率与 👍 率进入观察窗
  → 若 golden 回归失败或 👎 飙升 → 回切 primary 并出 Launch Card 结论
```

### 5.8 旅程 H：上线效果卡片（v1.1 / v1.5）

```
拟切换 rewrite 规则包
  → 离线 eval recall 前后对比
  → 填写预期：拒答率不变、FAQ 命中 +3pp、成本持平
  → 发布 → 48h 拉数
  → 达标归档 / 不达标回滚
```

---

## 6. 数据模型

### 6.1 实体关系（逻辑）

```
User 1──* Conversation 1──* Message
  │              │              │
  │              ├──0..1 HandoffSession（open 唯一）
  │              └──0..* Ticket
  │
  ├──* Feedback（per message）
  ├──* AuditLog（actor）
  └──* KnowledgeDraft（created_by / reviewed_by）

Document 1── 向量 chunks + 原文件（对象存储）
KnowledgeGap 0..1── KnowledgeDraft 0..1── Document
PromptTemplate 1──* PromptVersion（active 指针）
IntentConfig（路由映射）
ModelRouteConfig（purpose → primary/fallback 链）
AgentRun / RunStep（可选落库：步骤、工具、模型、token）
CostLedgerEntry（按 run 聚合费用）
LaunchCard（变更预期与实测）
```

### 6.2 关键枚举

| 枚举 | 值 |
|------|-----|
| UserRole | user, agent, admin |
| ConversationStatus | active, closed, transferred |
| MessageRole | user, assistant, system, staff |
| TicketStatus | pending, processing, resolved, closed |
| TicketPriority | low, medium, high, urgent |
| HandoffStatus | queued, claimed, resolved, returned, timed_out |
| DocumentStatus | pending, indexing, active, failed, archived |
| GapStatus | open, promoted, dismissed |
| DraftStatus | draft, approved, rejected |

### 6.3 一致性约束（实现红线）

| 约束 | 机制要求 | 违反后果 |
|------|----------|----------|
| 开放工单用户+标题唯一 | partial unique + 冲突收敛 | 重复单爆炸 |
| 一会话一开放 handoff | partial unique + 冲突回查 | 双坐席抢同一会话 |
| 工单创建统一仓储入口 | 禁止旁路 insert | 并发漏重 |
| staff 历史对 AI 可见 | 镜像为 assistant（或等价策略） | 暖回流丢人工上下文 |
| 配置缓存 epoch | 加载中 invalidate 丢弃结果 | 读到陈旧路由 / Prompt |
| 索引 write-new-then-delete | generation 世代 | 检索黑洞 |
| Loop 步数/工具次数上限 | 硬配置 | 死循环烧钱与挂死会话 |
| 工具仅 Registry 可执行 | 调用前校验 | 模型乱调高危能力 |
| 成本记账 best-effort | 失败不挡回复 | 主路径被监控拖死 |

---

## 7. 接口与集成面

### 7.1 REST 分组

| 前缀 | 主要能力 |
|------|----------|
| `/api/v1/admin/auth/*` | register / login / me |
| `/api/v1/chat/*` | conversations CRUD、history、feedback、WS |
| `/api/v1/rag/query` | 同步 RAG 查询（可带 filters） |
| `/api/v1/agent/classify` | 意图分类调试 / 集成 |
| `/api/v1/tickets/*` | 工单 CRUD |
| `/api/v1/embedding/*` | 上传 / reindex |
| `/api/v1/admin/documents` | 文档列表 / 删除 |
| `/api/v1/admin/intents` | 意图 CRUD |
| `/api/v1/admin/analytics` | 分析 |
| `/api/v1/admin/tickets*` | 管理工单与看板 |
| `/api/v1/admin/system/health` | 系统健康 |
| `/api/v1/admin/handoffs/*` | 接管 |
| `/api/v1/admin/prompts/*` | 模板与版本 |
| `/api/v1/admin/audit-logs` | 审计 |
| `/api/v1/admin/gaps/*` | 缺口 |
| `/api/v1/admin/drafts/*` | 草稿 |
| `/api/v1/admin/models/*` | 模型路由 CRUD / 试连（v1.1） |
| `/api/v1/admin/costs/*` | 成本汇总查询（v1.1） |
| `/api/v1/admin/agent-runs/*` | run 回放（v1.5） |
| `/api/v1/admin/launch-cards/*` | 效果卡片（v1.5） |
| `/health` | 深度健康 |
| `/metrics` | Prometheus（**无鉴权须网络隔离**） |

### 7.2 错误与安全约定

- 业务错误：统一 API envelope / 分页结构
- 认领冲突：409
- 未授权：401；角色不足：403
- 限流：429
- 生产不暴露 legacy 令牌进 URL 的 WS 路径

### 7.3 外部集成点

| 集成 | 配置 | 行为 |
|------|------|------|
| LLM（多 purpose） | `MODEL_ROUTES_*` / 分 purpose 的 LLM_* | 分类 / 改写 / 生成 / 摘要；fallback 链 |
| Embedding | EMBEDDING_* | 索引与检索 |
| 订单 webhook | ORDER_LOOKUP_* | search_order；失败降级 |
| 多模型网关（可选） | LITELLM_URL / OPENROUTER_* 等 | 统一转发与密钥托管 |
| MCP Servers（v1.5+） | MCP_SERVERS 列表 | 工具动态注册到 Registry |
| 价目表 | MODEL_PRICE_TABLE | 成本估算 |

协议能力（Chat Completions · Tool Calling · Structured Outputs · 不绑定 Assistants）见 §3.3 / §4.13.5。

**v2：** 通用连接器框架（订单 / CRM / ITSM）、出站事件 Webhook、IM / 邮件通道、可选代码沙箱。

---

## 8. 非功能需求

### 8.1 安全

| 需求 | 目标 | 分期 |
|------|------|------|
| 认证 | 全业务 API / WS 需身份 | MVP |
| 授权 | 三角色 RBAC | MVP（粗粒度） |
| 密钥 | 生产禁默认 SECRET | MVP |
| 注入防护 | Prompt 控制硬拒绝 | MVP |
| 传输 | TLS 终结在反代 | 运维 |
| 指标端点 | 勿公网裸奔 | 运维清单 |
| 脱敏 | 日志默认开 | MVP |
| 渗透 / 威胁建模 | 企业交付前完成 | v2 |
| SSO / MFA | 企业标准 | v2 |

### 8.2 隐私与合规

| 需求 | 分期 |
|------|------|
| 审计谁改了什么 | MVP |
| 日志 PII 遮罩 | MVP |
| 消息落库脱敏可选 | MVP |
| 用户导出 / 删除权 | v2 |
| 数据驻留与分级 | v2 |
| 审计防篡改 / SIEM | v2 |

### 8.3 可观测性

- **日志：** JSON 结构化 + trace_id + 可选 mask
- **健康：** 并发探活核心依赖，失败 503
- **指标（节选）：** HTTP 吞吐与延迟、RAG 查询、LLM token、意图分类、建单、订单 webhook 失败、handoff 超时、WS 在线、索引任务、LLM 失败、审计事件、构建版本

告警规则与 Grafana 看板：试点后按环境自建。

### 8.4 性能目标（建议，非合同 SLA）

| 项 | 建议目标 |
|----|----------|
| 首 token | P95 < 3s（不含冷启动 LLM） |
| 非流式工具查询 | P95 < 2s + 外部 webhook |
| 文档上传 API | P95 < 2s 返回（异步索引） |
| 并发 WS | 单实例数百级（需压测验证） |
| 单次 Loop 墙钟 | P95 < `LOOP_MAX_WALL_MS`（默认 45s） |
| 意图分类 | P95 < 1.5s（含小模型） |

### 8.5 成本与模型经济学（v1.1）

成本机制统一见 §4.14（路由 / 熔断 / 降级）、§4.15.3（缓存）、§4.17（记账与看板）。NFR 底线：① 每次 LLM 调用可按 purpose→model 归因费用；② 日/月预算阈值可配，触发告警与降级链；③ primary 档位合理性纳入配置评审（附录 E）。

### 8.6 可用性与扩展

| 项 | 要求 |
|----|------|
| 单实例参考拓扑 | MVP 可交付 |
| 索引多 worker 安全 | MVP |
| Handoff 清扫多 worker 安全 | MVP |
| WS cancel 多 worker | v1.5 收口 |
| Metrics 多 worker | v1.5 文档化方案 |
| 关键词索引跨 worker | 允许最终一致 |
| RPO / RTO | 备份至少覆盖 PG + 对象存储 |

### 8.7 质量工程

| 项 | 要求 |
|----|------|
| 后端 unit + 关键 integration | MVP 起持续补齐 |
| Loop 失败恢复路径单测 | MVP 起：超时 / 参数错 / 未配置 |
| 主路径 E2E | v1.5+ |
| 前端测试 + UX 走查清单 | v1.5+ / MVP 人工走查 |
| 离线 eval | MVP 具备；CI 门禁 v1.5+ |
| Launch Card 流程 | MVP 模板；v1.5 产品化 |
| 关掉 AI 辅助仍可维护核心 Loop | 工程文化要求：关键路径代码可读可测 |

### 8.8 工程实现约束（来自 Owner 能力模型）

| 约束 | 说明 |
|------|------|
| 主语言 | TypeScript 或 Python 至少一种达到生产级 |
| 前端 | React 能力为加分项；核心体验不「能跑就行」 |
| 禁止 | 仅 vibe-coding 不可审的编排逻辑 |
| 自研 Loop | 必须可指出状态机/图的代码位置与测试，而非「调用了某某框架」 |

---

## 9. 业务指标

### 9.1 目标值与口径

| 指标 | 目标 | 建议口径 |
|------|------|----------|
| FAQ 自动解答率 | ≥ 70% | faq/product 且未 handoff/ticket/拒答 的回合 / 总用户回合 |
| 检索准确率 | ≥ 85% | 离线 golden recall@k / citation 有效率 |
| 人工重复量下降 | 50% | 同期 gap frequency 与重复 ticket 标题 |
| 转人工认领及时率 | ≥ 90% | claimed_at - created_at ≤ 超时阈值 |
| 工单 SLA 达标率 | 按矩阵 | resolved 前 age ≤ 优先级 SLA |
| CSAT / 👍 率 | ≥ 4/5 或 👍≥80% | feedback |
| 首响时间改善 | 相对人工 -60% | 用户首条到助手首 token |
| 单位有效会话模型成本 | 基线后 -20%（v1.5 波次） | Σ 估算费用 / 有效会话（排除纯探针） |
| 工具最终成功率 | ≥ 95% | 成功或合规降级 / 尝试次数；不含用户主动取消 |
| Loop 触顶率 | 观察，趋降 | 达 MAX_STEPS / MAX_WALL 的 run 占比 |
| 模型 fallback 率 | 有预算，异常升高告警 | fallback 次数 / LLM 调用 |
| Prompt/检索缓存命中率 | 提升向好 | hits / eligible |
| Launch Card 闭环率 | 100%（适用变更） | 有预估且有窗口复盘的变更占比 |

### 9.2 运营日常看板

1. Dashboard：👎 率、harness fallback、intent 分布
2. Ticket dashboard：SLA 违约、oldest open
3. Handoffs：queued 堆积、timeout 计数
4. Gaps：frequency Top N
5. System：pending 索引积压、依赖红灯
6. Metrics：LLM failure、order webhook failure
7. **Cost（v1.1）：** 单位成本、purpose 占比、缓存命中、Top 贵会话
8. **Agent（v1.1）：** Loop 触顶、工具 error_class、fallback 率

---

## 10. 分期路线图

### 10.1 MVP（准生产试点）

**目标：** 可内测 2 周以上的私有化智能客服底座；Agent 编排具备 **可恢复的工具环 + 分 purpose 模型配置 + 成本记账骨架**。

| 能力 | 交付要点 |
|------|----------|
| Honest RAG | 混合检索、拒答、引用、自检、置信度 UI；查询改写（规则默认） |
| Agent 路由 + **Loop 骨架** | 6 意图、5 类节点、Harness；tool 路径多步/重试/预算 |
| 工具 + 槽位 | 订单查询示例 + 多轮补号 + 失败恢复 |
| **Model Router（配置级）** | purpose→primary/fallback；OpenAI 兼容；可说清选型理由 |
| **Cost Ledger（骨架）** | token/模型入账；基础 Admin 或 metrics |
| 上下文预算 | 历史裁剪、证据组装、ContextTrace |
| 工单 | 自动/自建、并发去重、基础看板 |
| 暖转人工 | 入队摘要、认领 409、超时建单回 AI |
| Knowledge Loop | Gap 聚合、Draft 审核发布、离线 eval |
| 运营平台 | 异步索引、意图/Prompt 热更、审计脱敏、健康与 metrics |
| 体验门槛 | 用户台核心路径通过 §4.19 走查 |
| 部署 | Compose 参考拓扑 + 生产检查清单 + Launch Card **模板** |

### 10.2 Wave A — 服务不黑洞（~10–15 人日）

| ID | 能力 | 要点 |
|----|------|------|
| E1 | 主动 SLA 引擎 | 按优先级 first_response / resolve；扫描 warning/breached；升级写审计 |
| E2 | 多通道通知中心 | WS + 邮件/Webhook/IM 之一；handoff/SLA/工单模板；HMAC 签名 |
| E4 | out_of_scope | 新意图 + 专用拒答；可选敏感域；指标与 eval |

### 10.3 Wave B — 坐席可规模化（~8–12 人日）

| ID | 能力 | 要点 |
|----|------|------|
| E3 | 技能组 / 排班 / 派单 | Team、忙闲、按意图路由、轮询/最少未结、本组成员可见队列 |

### 10.4 Wave C — 进得了企业 IT（~25–40 人日）

| ID | 能力 | 要点 |
|----|------|------|
| E5 | SSO | ✅ OIDC + JWKS 生产校验；JIT；角色映射；可选禁用本地注册（SAML 仍后置） |
| E6 | 连接器框架 | ✅ 配置化 HTTP；Admin 试调用；失败 mock 降级 |
| E7a | Web Widget | ✅ 访客 session；同一 Agent 流水线；`/widget` + embed 示例 |

### 10.5 Wave D — 治理与质量（~25–40 人日）

| ID | 能力 | 进度 |
|----|------|:----:|
| E8 | 质检与坐席分析 | ✅ 骨架：拒答/反馈率 + 确定性 score + Admin 页 |
| E9 | 数据导出/删除、SIEM、扩展 PII | 部分：用户导出/删除 ✅；SIEM 审计 export/push ✅；扩展 PII ⏳ |
| E10 | 知识发布 diff/回滚/效果卡片 | ⏳ |
| E11 | §9 指标产品化 + eval CI | ✅ Admin analytics + GitHub Actions eval |
| E14 | 主路径自动化测试补齐 | ✅ CI pytest |
| E21 | **Launch Card 产品化** + 自动回填在线指标 | ✅ CRUD + measure |
| E22 | **Agent Run 回放 UI** | ✅ `/admin/agent-runs` |

### 10.6 Wave E — 平台硬化与渠道（~15–25 人日）

| ID | 能力 |
|----|------|
| E12 | 多 worker：cancel / metrics / 索引失效收口 |
| E13 | 用户与权限 UI |
| E15 | Runbook：reindex / 模型轮换 / 三存储对账 |
| E7b | 飞书 / 企微 / 钉钉之一 | ✅ **飞书**事件订阅 + 同流水线；企微/钉钉仍后置 |

### 10.7 Wave F — Agent 平台增强（~20–35 人日，可与 D 并行）

| ID | 能力 | 要点 |
|----|------|------|
| E23 | 多模型网关 | LiteLLM/OpenRouter 类或自研等价；统一 fallback 与密钥 |
| E24 | MCP Client | 白名单导入工具到 Registry；默认只读 |
| E25 | 成本优化波次 | prompt cache、检索缓存、批量/降级策略；目标单位成本 -20% |
| E26 | 会话摘要压缩 | 长会话中段摘要；摘要 purpose 走小模型 |
| E27 | 扩展思考/复杂推理（可选） | 仅白名单意图；严格预算；默关 |
| E28 | 受控代码沙箱（可选） | 默认关；威胁建模通过后才试点 |

### 10.8 体验增强（P2，按需）

| ID | 项 |
|----|-----|
| E16 | 富媒体：图片/附件、截图报障 |
| E17 | i18n / 时区 |
| E18 | 多 Bot（业务线独立 prompt 与知识子集） |
| E19 | 访客模式（与 Widget 重叠） |
| E20 | 多租户 SaaS — **独立商业立项**，默认不在本 PRD 范围 |
| E29 | 前端动效打磨（Framer Motion / CSS）达到品牌级 |

### 10.9 企业闭环目标态

```
        ┌────────── 渠道 ──────────┐
        │ Web · Widget · 企微/飞书  │
        └────────────┬─────────────┘
                     ▼
              身份（SSO）+ 限流
                     ▼
         Harness → 意图 → ModelRouter → 路由
        /    |     |     |    \
     rag   tool  ticket handoff clarify
      │      │      │      │
      │      │      │      ├→ 技能组队列 → 坐席
      │      │      │      └→ SLA 扫描 → 通知中心
      │      │      └→ ITSM 连接器（可选）
      │      └→ Loop：Tool Registry / MCP / webhook
      ▼
  诚实回答 / 拒答 → 反馈 → Gap → Draft → 发布 → Eval
      │
      └→ CostLedger · RunTrace · LaunchCard · 审计 · 告警
```

### 10.10 推荐试点策略

1. **内测 2 周：** 单 worker + 真实知识库 + 1 个订单 webhook + 2 名坐席  
2. **看五数：** 自动解答率、handoff 超时、👎 率、**单位成本**、**工具最终成功率**  
3. **模型：** 先中档生成 + 小模型分类，用数据证明再升配（§4.14）  
4. **再开 Wave A / F：** 有超时与差评再上 SLA/通知；有成本痛点再上缓存网关  
5. **IT 评审前：** 审计抽查 + 部署清单 + SSO 排期 + 一次完整 Launch Card 演练  

---

## 11. 范围边界

### 11.1 在范围内

- 私有化智能客服：RAG、**自研 Agent 编排**、工单、转人工、知识运营、基础合规
- OpenAI 兼容多模型接入、分 purpose 路由与成本记账
- 上下文预算、查询改写、工具失败恢复
- MCP Client / 多模型网关 / 效果卡片（路线图）
- 单租户组织内多角色协作
- §10 所列企业增强项（作为路线图）
- 前端体验达到 §4.19 最低精致度

### 11.2 明确不在范围

1. 公有云多租户计费、配额、店铺市场
2. 语音呼叫中心 / 实时电话质检
3. 自研大模型训练与 RLHF 平台
4. 完整 ITSM（变更 / CMDB / 问题管理全模块）— 以连接器对接
5. 替代企业网盘 / Wiki 的全量知识创作套件
6. **开放式自主 Agent**（无限步数、任意工具、任意文件系统）— 客服场景默认禁止
7. 以托管 Assistants 线程替代自研 Loop 作为行为真相来源
8. 默认开启代码执行沙箱 / 高危写操作（须单独威胁建模与开关）

---

## 12. 验收标准

### 12.1 MVP 准生产试点

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | 登录后 WS 流式问答 | 手工 / 集成测 |
| 2 | 上传文档 → active → 问得到引用 | 手工 + 索引指标 |
| 3 | 弱检索拒答不胡编 | eval refusals + 手工 |
| 4 | 6 意图路由到 5 类节点 | 单元 + 手工 |
| 5 | 订单槽位 3 轮内完成或 clarify | 手工 |
| 6 | 工单去重并发正确 | 并发测试 |
| 7 | handoff 认领冲突 409；超时建单 | 手工 + 清扫任务 |
| 8 | Gap → Draft → Approve → 可检索 | 手工 |
| 9 | Prompt 激活热更新 | 手工（双实例更佳） |
| 10 | 审计有记录且 detail 脱敏 | 手工 |
| 11 | 默认 SECRET 生产拒启 | 启动测试 |
| 12 | `/health` 依赖异常 503 | 手工 |
| 13 | 工具超时走恢复策略且不出现死循环 | 单测 + 手工 |
| 14 | 至少 2 个 purpose 可配不同模型 | 配置 + 调用日志 |
| 15 | 单次对话可查模型名与 token/费用估算 | 日志或 Admin |
| 16 | 用户主路径通过 UX 走查清单 | 设计/研发联审 |

### 12.2 企业生产就绪（v2 / v3）

| # | 标准 |
|---|------|
| 1 | 分级 SLA 主动升级 + ≥1 离线通知通道 |
| 2 | SSO 登录与角色映射 |
| 3 | ≥2 业务连接器可配置 |
| 4 | 技能组派单 |
| 5 | out_of_scope 生效且 eval 不回退 |
| 6 | 用户管理 UI + 数据删除 / 导出 |
| 7 | 主路径 E2E 自动化 + eval CI |
| 8 | 多 worker 下 cancel / metrics 行为符合文档 |
| 9 | §9 核心指标 Admin 可见可告警 |
| 10 | 多模型网关 fallback 与成本看板可用 |
| 11 | 适用变更 100% Launch Card 闭环 |
| 12 | MCP 工具白名单可热更新且审计 |
| 13 | 单位会话成本相对基线可证明优化波次 |

---

## 13. 风险与依赖

| 风险 | 等级 | 缓解 |
|------|------|------|
| LLM 质量不稳导致误分类 / 胡编 | 高 | Harness + grounding 拒答 + eval |
| 知识陈旧 | 高 | Gap 雷达 + 固定运营节奏 |
| 转人工无人值守 | 高 | 超时清扫 + 通知中心（Wave A） |
| 多 worker 行为分叉 | 中 | 部署清单限制 + Wave E 收口 |
| Webhook 降级被当成真数据 | 中 | UI 标明 data_source；监控 failure |
| Prompt 热更新改坏分类 | 中 | 版本回滚 + 审计 + 编辑警示 |
| 合规审查卡壳 | 高 | 基础审计脱敏 + SSO / 数据主体权利 |
| 测试债 | 中 | 关键路径优先自动化 |
| 向量 / 关键词检索规模瓶颈 | 中 | 监控延迟；换引擎单独立项 |
| 依赖客户 IdP / IM 排期 | 中 | 接口 mock 并行开发 |
| 多模型行为不一致导致回归 | 高 | purpose 固定 eval 集；切换强制 Launch Card |
| Loop 死循环 / 成本爆炸 | 高 | 硬预算 + 熔断 + 单测 |
| 工具副作用（重复下单/误写） | 高 | side_effect 标签 + 幂等 + 默认只读 MCP |
| 「框架黑盒」不可调试 | 中 | 自研 Loop 为真相；框架仅适配 |
| 过度降本导致质量塌陷 | 中 | 成本与 👎/拒答同屏；禁单指标优化 |
| 上下文窗口误用 | 中 | Context Manager 强制裁剪与 trace |

**外部依赖：** 可用的多厂商 LLM / Embedding 端点（或网关）、SMTP 或 IM 机器人、客户订单 / CRM API、企业 IdP、（可选）MCP Server、价目表配置。

---

## 14. 附录

### 附录 A — 关键配置项（运营 / 运维）

| 配置项 | 建议默认 | 说明 |
|--------|----------|------|
| APP_ENV | production | development 才允许默认密钥等宽松项 |
| SECRET_KEY | （强制替换） | 生产必须替换 |
| DATABASE_URL | — | PostgreSQL |
| REDIS_URL | — | 队列 / 限流 / pubsub |
| 向量库连接 | — | 如 CHROMA_HOST/PORT |
| 对象存储 | — | MinIO / S3 |
| LLM_* / MODEL_ROUTES | — | 分 purpose；见 §4.14 |
| MODEL_PRICE_TABLE | — | 成本估算 |
| EMBEDDING_* | — | 维度变更需 reindex |
| BM25 索引路径 | 本地持久卷 | 多实例注意一致性策略 |
| ORDER_LOOKUP_WEBHOOK_URL | 空=mock | 订单工具 |
| ORDER_LOOKUP_TIMEOUT_S | 5 | |
| LOOP_MAX_*（STEPS / TOOL_CALLS / WALL_MS） | 6 / 4 / 45000 | Loop 硬预算，语义见 §4.13.3 |
| REWRITE_ENABLED | true | 默认规则改写 |
| REWRITE_LLM_ENABLED | false | MVP 建议关 |
| PROMPT_CACHE_ENABLED | true | 前缀稳定约定 |
| RETRIEVAL_CACHE_TTL_S | 0=关 | v1.5 可开 |
| MCP_SERVERS | 空 | v1.5+ |
| SANDBOX_ENABLED | false | 默认关 |
| JWT 过期分钟 | 1440 | |
| RATE_LIMIT_PER_MINUTE | 60 | |
| TICKET_SLA_HOURS | 24 | MVP 统计用；v2 换分级矩阵 |
| HANDOFF_PICKUP_TIMEOUT_MIN | 10 | |
| LOG_MASKING_ENABLED | true | |
| MASK_STORED_MESSAGES | false | 与摘要质量权衡 |
| CORS_ORIGINS | 前端源 | |
| DAILY_LLM_BUDGET | 空=不限制 | 触发降级可选 |

### 附录 B — 术语表

| 术语 | 含义 |
|------|------|
| RAG | 检索增强生成 |
| Grounding | 检索证据是否足够支撑回答 |
| Harness | 绕在 Agent 外的确定性安全与输出约束层 |
| **Agent Loop** | 规划→执行→观察→恢复的多步闭环（自研） |
| **Model Router** | 按 purpose 选择模型与 fallback 的调度器 |
| **Purpose** | 调用目的：classify / rewrite / generate / summary … |
| **Tool Registry** | 工具白名单与 schema / 权限 / 副作用元数据 |
| **MCP** | Model Context Protocol；外部工具标准接入 |
| **Cost Ledger** | 按 run 汇总 token 与估算费用 |
| **Launch Card** | 上线前预期 + 上线后验证的效果卡片 |
| **ContextTrace** | 单次 run 的上下文/检索/改写决策痕迹 |
| Handoff | 实时人工接管会话 |
| Gap | 知识缺口聚合记录 |
| Draft | 待审知识条目 |
| Slot filling | 多轮补齐工具入参 |
| Warm return | 人工结束后 AI 可见人工历史并恢复应答 |
| Honest RAG | 弱证据拒答 + 引用 + 自检 的产品叙事 |
| Structured Outputs | 约束模型输出 JSON/schema 的能力 |
| Function/Tool Calling | 模型发起结构化工具调用的协议能力 |

### 附录 C — 文档分工建议

| 问题 | 文档 |
|------|------|
| 产品要解决什么、功能边界、分期与验收 | **本 PRD** |
| Agent 改代码时必须遵守的行为契约 | `docs/contracts/agent-behavior.md` + `packages/contracts/agent` |
| 上下文 / 改写 / 流水线 | `docs/architecture/*` |
| 监控 / 成本指标 | `docs/observability/*` |
| 某模块实现是否落地、测试是否齐 | 实现状态 / STATUS |
| 怎么部署上线 | 部署清单 / Runbook |
| 为什么选某模型/某 Loop 方案 | `docs/adr/*` + 附录 E 权衡表 |

### 附录 D — SLA 策略表示例（v2）

| priority | first_response | resolve | escalate_to |
|----------|----------------|---------|-------------|
| urgent | 15m | 4h | duty_manager_webhook |
| high | 1h | 8h | l2_queue |
| medium | 4h | 24h | banner_only |
| low | 24h | 72h | weekly_report |

### 附录 E — 方案权衡记录模板（强制）

> 重大编排/模型/工具决策必须填写，进入 ADR 或 PR 描述。

| 字段 | 内容 |
|------|------|
| 问题 | 要解决什么？成功长什么样？ |
| 路径 A | 做法、预估成本、质量、复杂度、风险 |
| 路径 B | 同上 |
| （可选）路径 C | 同上 |
| 推荐 | 选哪条，**为什么这个模型/方案适合这个任务** |
| 否决 | 为什么不用「最贵模型 / 最重框架 / 无限 Agent」 |
| 度量 | 上线后看哪些指标证明对了（链到 Launch Card） |
| 回滚 | 如何 1 步撤回到上一稳定策略 |

### 附录 F — Launch Card 模板（MVP 可用 Markdown）

```markdown
# Launch Card: <标题>
- 日期 / 负责人 / 关联 PR:
- 变更类型: Prompt | ModelRoute | LoopBudget | Tool | Other
- 预期指标: 
  - FAQ 解答率: 
  - 拒答率: 
  - 👍 率: 
  - 单位会话成本: 
  - TTFT P95: 
- 离线 eval: before → after
- 风险与回滚:
- 观察窗口: 48h
- 实测结论: （上线后填）达标 / 观察 / 回滚
```

### 附录 G — v1.0 → v1.1 变更对照

| 主题 | v1.0 | v1.1 | 详见 |
|------|------|------|------|
| Agent | 单轮路由 + 槽位 | + Multi-step Loop / 恢复 / 硬预算 | §3.5 · §4.13 |
| 模型 | 单一 OpenAI 兼容端点 | + Purpose 路由、fallback、能力画像 | §4.14 |
| 成本 | 未一等公民 | + Cost Ledger、预算、缓存策略 | §4.15 · §4.17 |
| 工具 | webhook 内置 | + Registry 契约；MCP/沙箱路线图 | §4.16 |
| 可观测 | 业务 metrics | + run 回放、费用、质量闭环 | §4.17 |
| 发布 | 审计 | + Launch Card 预估与验证 | §4.18 |
| 体验 | 功能页 | + UX Bar 与走查清单 | §4.19 |

---

**文档结束（v1.1 — Agent 编排与多模型平台增强）**

下一步建议：

1. 按 §10.1 拆 MVP 任务板（**Orchestration / Model Router / RAG / 前端体验 / 运维 / 评测**）
2. 用附录 E 对「自研 Loop vs 框架」「主生成模型选型」做一次书面权衡并落 ADR
3. 同步更新 `docs/contracts/agent-behavior.md` 与 `docs/architecture/agent-pipeline.md` 中的 Loop 状态机
4. 选定 Wave A 与 Wave F 中成本最低的 1–2 项（通常 `out_of_scope` 或缓存命中）
5. 准备首份 Launch Card 模板试跑（即使仍是 Markdown）
