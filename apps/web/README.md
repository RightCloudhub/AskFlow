# AskFlow Web

React + Vite 企业客服前端（用户台 + 管理台）。UI 以 Ant Design 为主，数据层对齐 RAGFlow 分层实践。

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
```

**约定**

- 页面 → `services/*` → `api/client`；禁止页面内拼 fetch。
- Query key 仅用 `hooks/query-keys.ts` 工厂。
- 对话优先 **WebSocket 流式**（`/api/v1/chat/ws`），失败可再走 REST。
- 接管：认领后可拉消息 + `POST .../reply` 座席回复。

```bash
npm run build   # tsc --noEmit + vite build（manualChunks 分包）
```
