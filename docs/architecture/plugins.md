# 可插拔架构（L2）

| 项 | 内容 |
|----|------|
| **目标** | 功能可关、可组合；官方 profile 交付 |
| **非目标** | 第三方热加载 / 版本隔离（L3） |
| **估算** | [pluggable-architecture-estimate.md](../engineering/pluggable-architecture-estimate.md) |

## 1. 概念

| 组件 | 路径 | 作用 |
|------|------|------|
| Manifest | `packages/contracts/features.yaml` | profile + 插件依赖图 |
| SPI | `apps/api/app/plugins/` | `Plugin.register` → routes / handlers / tools / nav |
| 装配 | `load_plugins()` in `create_app` | 拓扑排序后注册，挂到 `AppContext` |
| Pipeline | `services/agent/pipeline/handlers/*` | `RouteHandler` 表驱动分发 |
| Side effects | `services/chat/side_effects/*` | ticket / handoff / gap / cost |
| 前端 | `apps/web/src/plugins/*` | 按 features 过滤 Admin 导航与路由 |

## 2. Profile

| Profile | 用途 |
|---------|------|
| `core-only` | 仅 auth / chat / health / audit / users |
| `faq-only` | core + rag |
| `mvp` | 客服主路径（无企业增强） |
| `enterprise` | mvp + SLA/SSO/teams/… |
| `full` | **默认**；与改造前行为一致 |

环境变量：

```bash
ASKFLOW_PROFILE=mvp
ASKFLOW_FEATURES=+sla,-mcp   # 可选增量
```

前端：

```bash
VITE_ASKFLOW_FEATURES=core,rag,ticket   # 可选；否则拉取 /api/v1/admin/features
```

## 3. 插件边界

见 `features.yaml` 的 `plugins.*.depends`。启动时自动闭包依赖；缺依赖或未知 id 则 **fail-fast**。

## 4. 扩展点

```python
class Plugin(Protocol):
    id: str
    depends: list[str]
    def register(self, ctx: AppContext) -> None: ...
```

`AppContext` 槽位：

- `api_router` / `admin_router`
- `route_handlers`（pipeline 路由）
- `side_effect_handlers`
- `tool_registry`
- `admin_nav`

查询已加载：`GET /api/v1/admin/features`（agent/admin）。  
Admin 管理页：`/admin/plugins`（core 插件，只读展示 profile / 插件目录 / 扩展点）。

### 发现接口与管理页（2026-10-03）

发现数据由 `app/plugins/discovery.py` 统一生成，页面通过 `features-service.ts`、`useFeaturesDiscovery` 与 query key 获取。

| 响应字段 | 含义 |
|---|---|
| `profile` / `profiles` | 当前档位 / manifest 中可用档位 |
| `features` / `loaded` | 已启用集合 / 实际注册的插件顺序 |
| `feature_deltas` | 当前 `ASKFLOW_FEATURES` 配置文本 |
| `plugins` | 全部插件的 `id`、`depends`、`enabled`、`loaded` |
| `admin_nav` | 后端注册的导航，包含插件、路径、标签与排序 |
| `route_handlers` / `side_effects` | 已装配的 Pipeline 路由与副作用名称 |

管理页展示统计、插件依赖和扩展点，不提供启停、安装或热加载接口。调整 `ASKFLOW_PROFILE` / `ASKFLOW_FEATURES` 后重启 API。`VITE_ASKFLOW_FEATURES` 仅覆盖前端 feature 列表，不改变后端注册结果；页面展示的发现数据仍来自后端。

服务任务另有 `SERVICE_TASKS_ENABLED` 和 `SERVICE_TASKS_GOALS`，前者结合 Agent 插件决定受理与 worker 启动，后者控制新聊天目标接管；它们不等同于插件开关。默认值与已有任务处理见 [API README](../../apps/api/README.md#service-tasks-and-order-connector)。

## 5. 数据层策略

**关插件仍留表**（迁移全量 schema 不变）。拔插件 = 不挂路由 / 不注册 handler / 不跑 worker。

## 6. 冷契约

`LEGAL_ROUTES` / `LEGAL_INTENTS`、Harness 拒答语义、loop 预算 **不可** 由插件热改；变更走契约 + 测试冷更新。

## 7. 验收

1. `ASKFLOW_PROFILE=full` 下现有 pytest / eval 绿  
2. `core-only` 时 `/api/v1/rag/*`、`/tickets` 为 **404**  
3. Pipeline `runner.py` 表驱动；handler 分文件  
4. 前端 Admin 导航随 features 收敛  
