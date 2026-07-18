# AskFlow — Agent / 贡献者工程约定

企业智能客服系统（RAG + Agent），单租户、可私有化部署。FastAPI 后端 + SQLAlchemy async + Pydantic；React + Vite 前端；Redis/MinIO/OpenAI 兼容 LLM；Prometheus/Grafana 可观测。

## 项目入口
- API：`apps/api/app/main.py`（`app = create_app()`）；启动：`uvicorn app.main:app --reload --port 8000`
- Web：`apps/web/src/main.tsx` → `App.tsx`（React Router + `FeaturesProvider`）
- 配置：`apps/api/app/core/config.py`（Pydantic `Settings`，环境变量见 `.env.example`）
- 前端 API：`apps/web/src/api/client.ts`（`getToken()` / fetch 封装）
- 共享类型/契约：`packages/shared-types/`、`packages/contracts/`

## 命令（均在对应目录下运行）
```bash
# API 依赖
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # 或: pip install -e ".[dev]"

# API 测试（pytest，asyncio auto；conftest 每例隔离内存 SQLite + ASGITransport）
cd apps/api && source .venv/bin/activate && PYTHONPATH=. pytest -q
#   - tests/unit（纯逻辑）/ tests/integration（API+DB）/ tests/e2e（.gitkeep 占位）
#   - CI 环境变量：ASKFLOW_ENV=test SECRET_KEY=... DATABASE_URL=sqlite+aiosqlite:///:memory: ASKFLOW_PROFILE=full
# API lint / 格式化（ruff 在 dev extras 中）
cd apps/api && ruff check . && ruff format --check .

# 离线评测（golden / refusals；CI 也跑）
PYTHONPATH=apps/api python evals/runners/run_eval.py

# 代码硬性指标门禁（仓库根目录）
python3 scripts/ops/check_code_metrics.py

# Web
cd apps/web && npm install
npm run dev            # vite 开发
npm run build          # tsc --noEmit && vite build
npm run preview        # vite preview
```
完整本地启动见 `README.md`（dev compose、环境变量、SQLite/Postgres 切换）。

## 架构（负载模块）
- **API 路由**：`apps/api/app/api/v1/`（admin / agent / channels / chat / embedding / health / plugins / rag / tickets / widget）
- **业务服务**：`apps/api/app/services/`（agent / chat / rag / ticket / handoff / knowledge / prompt / auth / audit / notify / launch_card / qc / team 等）
- **RAG / Agent 核心**：查询改写 `services/rag/query_rewrite/`、上下文组装 `services/rag/context/`、Honest RAG grounding、Agent harness/意图/路由
- **数据层**：`apps/api/app/core/database.py` + `models/`（SQLAlchemy async）、`alembic/` 迁移
- **可观测/安全**：`middleware/logging`、`middleware/metrics`、`middleware/rate_limit`、`core/security.py`
- **插件/特性**：`plugins/` + `packages/contracts/features.yaml`、Web `src/plugins/` 做路由过滤
- **后台**：`workers/`（index_worker / enterprise_jobs / 周期性清扫）
- **评测**：`evals/`（golden / refusals / runners）

## CI（`.github/workflows/ci.yml`）
- `api-pytest`：Python 3.12，`apps/api` 下 `pytest -q`
- `offline-eval`：`PYTHONPATH=apps/api python evals/runners/run_eval.py`
- `web-build`：Node 20，`npm ci && npm run build`（含 `tsc --noEmit`）
- 本地复刻 CI 测试：`cd apps/api && ASKFLOW_ENV=test DATABASE_URL=sqlite+aiosqlite:///:memory: ASKFLOW_PROFILE=full pytest -q`

## 文档入口
- 产品与状态：`docs/prd/PRD.md`、`docs/STATUS.md`
- 目录映射：`docs/prd/STRUCTURE.md`
- Agent 行为契约：`docs/contracts/agent-behavior.md`
- 工程支柱：`docs/architecture/pillars.md`（安全兜底 / 性能 / 记忆可观测）

## 强制：代码硬性指标（完整见 [docs/engineering/code-metrics.md](./docs/engineering/code-metrics.md)）
适用 `apps/`、`packages/`、`evals/runners/`、项目脚本（不含 `node_modules/.venv/` 生成物）；新代码与改动代码必须满足，修改已超标文件须先拆分或同 PR 收敛。

| 指标 | 上限 |
| --- | --- |
| 函数长度 | ≤ 50 行（不含空行） |
| 文件大小 | ≤ 300 行 |
| 嵌套深度 | ≤ 3 层 |
| 位置参数个数 | ≤ 3（超出用 dataclass / TypedDict / Pydantic model / 对象参数） |
| 圈复杂度 | 每函数 ≤ 10 |
| 魔数（魔法数字） | 禁止；须提取命名常量（阈值/超时/重试/步数/业务数字尤其） |

### 合规写法
- 早返回（guard clause）控嵌套；多分支路由用字典/表驱动或策略对象，避免长 `if/elif`。
- `try` 只包最小失败点；不要整段业务套一层 try。
- 参数 >3 封装结构体（Py：dataclass/Pydantic；TS：对象参数 `opts: FooOptions`）。
- 阈值、超时、重试、步数、预算等不得裸字面量，必须命名常量或配置项。
- 单元测试 `pytest`；前端最小 client 检查 `npm run test:client`；Web 构建含 `tsc --noEmit`。

## 约定（从代码推断）
- Python ≥ 3.11（CI 用 3.12）；使用 `from __future__ import annotations`；类型注解优先现代 union（`str | None`）。异步优先（FastAPI + SQLAlchemy async + `pytest-asyncio` auto mode）。
- 设置统一从 `Settings` 读，不要重复写环境变量 / 默认值；`get_settings()` 是缓存入口。
- API 路径统一走 `/api/v1` 前缀（`settings.api_prefix`）；健康/指标在根 `/health`、`/metrics`。
- 敏感配置用 `SecretStr`，不要泄露；本地 demo 密钥仅用于 development/test。
- 前端功能按 `features.yaml` + `FeaturesProvider` 做可插拔路由。

## Notes
<!-- 后续快速补充：环境细节、CI 门禁命令、常用调试方式等 -->
