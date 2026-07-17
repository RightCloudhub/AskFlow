# AskFlow Web

React + Vite 用户工作台（MVP 骨架）。

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

打开 http://localhost:5173 — Vite 已代理 `/api` 到后端。
