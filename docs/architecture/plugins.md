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

## 5. 数据层策略

**关插件仍留表**（迁移全量 schema 不变）。拔插件 = 不挂路由 / 不注册 handler / 不跑 worker。

## 6. 冷契约

`LEGAL_ROUTES` / `LEGAL_INTENTS`、Harness 拒答语义、loop 预算 **不可** 由插件热改；变更走契约 + 测试冷更新。

## 7. 验收

1. `ASKFLOW_PROFILE=full` 下现有 pytest / eval 绿  
2. `core-only` 时 `/api/v1/rag/*`、`/tickets` 为 **404**  
3. Pipeline `runner.py` 表驱动；handler 分文件  
4. 前端 Admin 导航随 features 收敛  
