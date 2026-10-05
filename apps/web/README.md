# AskFlow Web

React + Vite 企业客服前端（用户台 + 管理台）。UI 以 Ant Design 为主，数据层对齐 RAGFlow 分层实践。

面向首次配置用户的说明见 [配置指南](../../docs/configuration/README.md)，尤其是 [前端功能列表与后端同步](../../docs/configuration/features.md) 和 [网站地址与代理配置](../../docs/configuration/access.md)。

## 开发

```bash
# 终端 1：API
cd apps/api && source .venv/bin/activate
export ASKFLOW_ENV=development SECRET_KEY=dev-secret-change-me
export DATABASE_URL=sqlite+aiosqlite:///./askflow.dev.db
uvicorn app.main:app --reload --port 8000

# 终端 2：Web
cd apps/web && npm install && npm run dev
```

打开 http://localhost:5173 — Vite 代理 `/api`（含 WebSocket）到后端。

## 架构

```
src/
  api/           # HTTP：api / apiForm / token / types
  services/      # 领域 API + chat-ws（流式）
  hooks/         # TanStack Query + query-keys
  stores/        # Zustand（引用侧栏）
  providers/     # QueryClient + ConfigProvider + Features
  components/
    chat/        # Markdown、流式气泡、引用、座席气泡、转人工横幅
    layout/      # 用户端 AppShell
    handoff/     # 收件箱 + 接管工作台（消息/回复）
    ticket/      # Form / List / Board / Detail
    admin/       # 图表、版本抽屉
  pages/         # 路由页面（lazy chunk）
  plugins/       # features 类型、导航注册、按插件门控
```

**约定**

- 页面 → `services/*` → `api/client`；禁止页面内拼 fetch。
- Query key 仅用 `hooks/query-keys.ts` 工厂。
- 对话优先 **WebSocket 流式**（`/api/v1/chat/ws`），失败可再走 REST。
- 接管：认领后可拉消息 + `POST .../reply` 座席回复。

## 插件与能力

`/admin/plugins` 由 core 插件提供，agent/admin 可查看当前 profile、feature 增量、插件依赖、启用/加载状态、Pipeline 路由、副作用与后端 Admin 导航。数据来自 `GET /api/v1/admin/features`，经 `features-service.ts` → `useFeaturesDiscovery` → `PluginsPage.tsx` 展示。

此页面只读。修改后端 `ASKFLOW_PROFILE` / `ASKFLOW_FEATURES` 后重启 API；前端导航与路由按 features 收敛。`VITE_ASKFLOW_FEATURES` 可覆盖前端 feature 列表，但不会启用后端插件。完整配置见 [可插拔架构](../../docs/architecture/plugins.md)。

## 服务任务交互

命中启用目标的聊天消息先返回任务受理确认，后台 worker 再把结果保存为会话消息。当前没有专门的任务/偏好管理页或后台结果 WebSocket 推送；重新读取会话消息可取得持久化进展，任务查看与取消可使用 [任务 API](../../docs/architecture/customer-service-lifecycle.md)。

```bash
npm run build   # tsc --noEmit + vite build（manualChunks 分包）
```
