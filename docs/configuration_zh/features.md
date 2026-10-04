# 功能与 Web 界面

[配置指南](README.md) · 下一篇：[模型与答案质量](models.md)

**Profile** 是一组功能包。**插件（plugin）** 是单个功能，例如工单或知识搜索。Profile 名称描述的是功能包，不是安装质量，也不保证可投入生产。

## 选择后端 profile

在 API 环境中设置 `ASKFLOW_PROFILE` 并重启：

| Profile | 包含的功能 |
| --- | --- |
| `core-only` | 核心账号、会话和基本管理；没有知识搜索插件 |
| `faq-only` | 核心，加上知识搜索和文档管理 |
| `mvp` | 核心、知识搜索、agent、工具、工单、转人工、知识草稿/缺口、运营设置、成本、微件 |
| `enterprise` | `mvp`，加上 SLA、通知、SSO、团队、连接器、上线卡片、分析、MCP、飞书、质检 |
| `full` | `enterprise`，加上企业微信和钉钉；默认值 |

对于简单的仅信息类服务：

```dotenv
ASKFLOW_PROFILE=faq-only
SERVICE_TASKS_ENABLED=false
```

对于更广泛的支持工作区：

```dotenv
ASKFLOW_PROFILE=full
```

Profile 会启用代码和路由。它不提供模型凭据、不连接订单系统、不创建客服人员，也不配置即时通讯机器人。

## 添加或移除选定的功能

`ASKFLOW_FEATURES` 更改所选的 profile。在功能前加 `+` 表示添加，加 `-` 表示移除：

```dotenv
ASKFLOW_PROFILE=mvp
ASKFLOW_FEATURES=+teams,+notify,-mcp
```

依赖项会自动添加。例如，`teams` 需要 `handoff`，`sla` 需要 `ticket`。移除一个必需的依赖项并不会移除所有使用它的东西：它可能会被重新添加回来。必要时也移除依赖它的功能，然后检查最终加载的列表。

在禁用对某个服务的暴露时，这一点很重要。不要仅凭一个 `-feature` 条目就推断出有效的功能列表。

| 功能 ID | 通俗含义 |
| --- | --- |
| `core`, `rag`, `agent`, `tools` | 核心、知识搜索、请求处理、工具支持 |
| `ticket`, `handoff`, `teams` | 工单、人工支持、客服组 |
| `knowledge`, `ops` | 知识缺口/草稿工作流和回复配置 |
| `cost`, `analytics`, `qc`, `launch` | 成本报表、运营报表、质检、变更记录 |
| `sla`, `notify` | 服务时间检查和通知 |
| `sso`, `connectors`, `mcp` | 公司登录、业务连接器、工具注册扩展 |
| `widget`, `feishu`, `wecom`, `dingtalk` | 客户联系渠道 |

确切的包和依赖项在 [features.yaml](../../packages/contracts/features.yaml) 中。未知的所选 profile 或功能会导致启动失败。请使用上面的 ID，而不是翻译后的菜单标签。

## 保持 Web 应用同步

浏览器可以从后端发现功能，但当前的功能发现端点需要客服或管理员账号。应用加载时会尝试发现。如果失败，界面只显示核心功能。因此，即使后端支持工单，普通客户也可能看不到工单链接。

对于有普通客户账号的部署，请在 `apps/web/.env.local` 或 Web 构建环境中提供一个匹配的非机密列表。这是一个**完整列表**，不是 `+`/`-` 调整，也不是 profile 名称。

对于 `faq-only`：

```dotenv
VITE_ASKFLOW_FEATURES=core,rag
```

对于 `mvp` 加上 `teams` 和 `notify`：

```dotenv
VITE_ASKFLOW_FEATURES=core,rag,agent,tools,ticket,handoff,knowledge,ops,cost,widget,teams,notify
```

编辑开发 Web 环境后请重启 `npm run dev`。对于已经构建的 Web 应用，请在 `apps/web` 中运行 `npm run build`，并让运维人员发布新的 `dist` 输出。更改 API 环境变量无法修改已经构建的 Web 包。

Web 列表只控制可见的导航和路由。后端授权仍然适用，因此某些客服或管理页面可能对无法使用它们的账号可见。后端已禁用的功能无法通过此列表启用。

如果使用管理员账号进行自动发现，请在登录后重新加载。要恢复到自动发现，请移除 `VITE_ASKFLOW_FEATURES` 并重启或重新构建 Web 应用。

## 验证和撤销

1. 更改 profile 或功能列表后重启 API。
2. 使用客服/管理员账号打开 **Admin → 插件与能力 (Plugins and capabilities)**。
3. 检查 **Profile**、**启用 (Enabled)** 和 **已加载 (Loaded)**。
4. 如果你使用覆盖，请更新 Web 列表，然后重启/重新构建 Web 应用。
5. 测试实际的客户操作，例如打开并创建工单。

此管理页面是只读的。要撤销更改，请恢复先前的环境值并重复重启/重新构建过程。隐藏与任务相关的功能不会取消先前已受理的工作。
