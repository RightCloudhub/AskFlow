# 待运行验证清单（本轮禁止执行）

2026-10-29：用户要求 code only。本轮测试、eval、构建、迁移、lint、指标、扫描、压测、部署 **全部未执行**。下列步骤供后续验证，失败优先修复；不得把编写测试当作通过。测试数量、通过率、覆盖率、QPS/P99 都没有当前实测值。

## 准备与基线

保留原 .env 修改、先备份数据库与财务记录。安装依赖属于验证阶段，不在本轮执行。所有后端命令在 apps/api，指标/eval/压测入口按注释 cwd。

```bash
cd apps/api
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
ASKFLOW_PROFILE=full python -m pytest -q --junitxml=test-results/baseline.xml
cd ../..
PYTHONPATH=apps/api python evals/runners/run_eval.py
PYTHONPATH=apps/api python evals/runners/run_mall_eval.py
ruff check apps/api/app/commerce apps/api/app/plugins/builtin/mall_*.py
python3 scripts/ops/check_code_metrics.py
git diff --check
```

指标脚本扫描全仓；分别记录改动文件和既有违规，不伪造零违规。测试数据例外只放宽魔数，生产代码仍不出现裸业务阈值。涉及旧超标文件先拆分，不能把新逻辑堆进去。

## 双档业务矩阵

商城 fixture 必须每测试清 get_settings/cache/AppContext，隔离 sessions，卸载全局端口。内存 SQLite 适用于 API 流程；一致性压测用文件 SQLite 多连接或 PG，不拿 StaticPool 的单连接证明锁安全。

```bash
cd apps/api
ASKFLOW_INFRA=lite python -m pytest tests/mall -q --cov=app.commerce --cov-report=xml --cov-report=term-missing
pip install -e '.[mall-full]'
MALL_REQUIRE_FULL=1 MALL_TEST_DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow_mall_test MALL_TEST_REDIS_URL=redis://localhost:6379/15 python -m pytest tests/mall -q --cov=app.commerce --cov-report=xml --cov-fail-under=85
python -m coverage report --include='*/commerce/payment/*,*/commerce/wallet/*,*/commerce/order/refunds.py,*/commerce/referral/*' --fail-under=95
cd ../..
MALL_TEST_DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow_mall_test MALL_TEST_REDIS_URL=redis://localhost:6379/15 PYTHONPATH=apps/api python evals/runners/run_mall_eval.py --full --output artifacts/mall-eval-full.xml
```

必须确保 full fixture 真使用 PG/Redis，不能把 full 配置名套到 memory 实现。服务连接失败应失败而非静默 skip。全量旧 pytest/eval 仍保持无LLM、Redis、PG可运行。

此业务 fixture 的 full 参数显式覆盖搜索为 LIKE、对象存储为 local，保留 PG/Redis 协调与 Streams；它不是所有 full 适配器的合同测试。S3、ES、SMTP、SMS、RabbitMQ、Kafka、只读副本与断连矩阵须单独验证；当前这些完整证据尚缺。缓存命中、外发和队列故障不能由 SQLite 业务测试代替。

| 测试组 | 必须断言 |
|---|---|
| account/security | 邮箱/短信验证TTL/次数/频率；密码重置吊销；refresh旧token重放整family；TOTP/恢复码单用；旧登录/WS/OIDC防MFA绕过；枚举相近耗时/相同响应 |
| profile | mall/mall-lite/mall-only/full/core-only路由；mall-only无Agent/RAG；显式+mall_order依赖闭包；关模块后台也404 |
| catalog/cart | 下架缓存不影响DB拒购；主库重新计价；图片类型/路径/权限/重复上传；地址归属、默认切换版本失效和重复删除；游标稳定且无深OFFSET |
| inventory | 1000并发抢100件，准确100订单；可用/预占非负，订单对应；支付/取消/超时抢CAS；两方言 |
| order/idempotency | 同key10并发只有1订单/预占；key改请求409；checkout单用；非法状态409；A查B404 |
| payment/refund | HMAC伪造拒绝；已签名畸形JSON/字段422；币种/金额/商户比对；100次回调只1journal；同流水异内容冲突；丢回调查单；晚付取消不复活；部分退款总额含pending额度 |
| wallet/reconcile | 200并发扣/充余额正确且非负；每journal借贷等；hash链连续；只追加限制；维护篡改能被对账发现；双人调账不能自批 |
| referral/risk | 同设备10注册奖励限额；关系并发绑定唯一；手机号必须验证；首单/延期/退款冲正；余额不足追偿不扣负；共享IP不直接封禁 |
| support/Gateway | 聊天查真实本人订单；取消确认/L2/库存释放/INTENT→EXECUTED；退款越权拒绝/超限审批；工单/回复outbox≤5秒通知 |
| notify/workers/ports | off邮箱短信仍站内信；event不重复；quiet hours/频控/死信；租约过期/fence；Redis中断安全降级；每端口各实现合约 |

覆盖率整体商城 ≥85%，资金 payment/wallet/refund/referral ≥95%；独立报告资金模块，不能用其他简单模块高覆盖掩盖资金缺口。

`tests/mall/test_chat_eval.py` 用实际 ChatTurn 驱动查单、取消确认与库存释放／台账、其他客户退款拒绝。商城 cases.jsonl 是场景说明，runner 以 pytest 场景输出 JUnit；原离线 eval 必须独立运行，不能用商城 eval 替代。

## 迁移与部署

```bash
cd apps/api
DATABASE_URL=sqlite+aiosqlite:///./mall-migration-check.db alembic upgrade head
DATABASE_URL=sqlite+aiosqlite:///./mall-migration-check.db alembic downgrade 20261016_document_metadata
DATABASE_URL=sqlite+aiosqlite:///./mall-migration-check.db alembic upgrade head
DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow_migration_check alembic upgrade head
DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow_migration_check alembic downgrade 20261016_document_metadata
DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow_migration_check alembic upgrade head
```

空库、已有create_all库、已有旧head库分开验证；核对所有表、FK/unique/check、索引、只追加trigger、schema drift。生产 downgrade 会丢商城数据，仅在一次性验证库执行。migration job 必须单副本，API启动不create_all生产库。

```bash
docker compose -f infra/compose/lite/docker-compose.yml up --build
# 先按 runbook 准备 prod/.env、独立密钥、对象访问域名和 HTTPS
docker compose -f infra/compose/prod/docker-compose.yml up --build
kubectl kustomize infra/k8s/overlays/lite
kubectl kustomize infra/k8s/overlays/full
```

两档均从注册→验证→订单→mock支付→退款→钱包→邀请→工单走通；检查可关闭端口、readiness和worker。PG主从切换/Redis故障演练独立留证，不以compose有副本当作自动容灾通过。

对已有 create_all 库先只读核对结构及 Alembic revision，再决定 stamp 的历史修订；不能直接 stamp head。新库的 core baseline downgrade 保留旧客服表属于有意的数据保护，双向验收重点是商城表/触发器的创建与移除，以及旧业务数据不丢失。

## 前端、扫描与负载

```bash
cd apps/web
npm ci
npm run build
npm run test:mall
npm audit --omit=dev
cd ../api
pip-audit
bandit -r app/commerce -ll
cd ../..
k6 run scripts/loadtest/mall-smoke.js
k6 run scripts/loadtest/mall.js
```

前端验证页面路由/权限菜单、客户JWT刷新单飞、认证/支付/订单/客服关键流程；保留theme。压测先seed/预热，报告写performance.md；初轮校准不降低零超卖/资金平衡不变量。CI缩小冒烟与完整手动负载分别执行。

共享请求客户端和商城请求客户端必须复用一次 refresh；验证后台停留到 access 过期后能继续操作、撤销家族不能继续聊天、WebSocket 在续期后重新认证。`test:mall` 包含菜单权限与 session 测试源码；它不能替代真实浏览器环境的 CSRF/Secure/SameSite 测试。

### 浏览器冒烟（隔离开发环境）

先启动启用 `MALL_DEMO_MAILBOX_ENABLED=true` 的一次性 development 部署，完成迁移；用相同 `DATABASE_URL` 运行 seed。演示收件箱不能在生产开启。以下独立 npm 包按需安装，不加入 lite API 依赖：

```bash
# 仓库根目录，seed 不允许 production/staging
PYTHONPATH=apps/api python scripts/loadtest/seed.py --users 2
cd scripts/e2e
npm install
npx playwright install chromium
MALL_E2E_URL=http://127.0.0.1:8000 node mall.mjs
```

脚本通过 API 创建新账号，在浏览器登录／加购／下单／mock 付款并检查普通客户无法访问财务管理；全界面、多设备、双人审批和外部 OIDC 跳转 E2E 仍需补充。seed 文件含凭据，仅保留于本地 `artifacts/`，不能上传为 CI 附件。

### CI 与手动负载入口

- 原 `.github/workflows/ci.yml` 继续原客服离线回归。
- `mall.yml`：PG/Redis 双档业务矩阵、覆盖率、双方言迁移、商城 eval 与缩小 k6 冒烟。
- 同一工作流另渲染 Compose／Kubernetes 配置并分别运行 lite／full 商城 eval；配置渲染不能替代实际部署。
- `mall-security.yml`：ruff/bandit、基线与本分支依赖差异、前端构建和 helper 测试。
- `mall-load.yml`：仅 workflow_dispatch，选择 lite/full、场景、RPS 与账号数；产出 summary JSON。full 在该工作流显式使用 FTS/local，PG、Redis 与压测器共享 hosted runner，因此不能作为指定独立硬件的正式容量证明。正式压测按 loadtest README 在专用环境逐场景运行。

CI 文件写入不表示已触发或已通过；本轮没有推送或手动运行工作流。

2026-10-30 补写会话轮换／退出竞争、迟到响应、WebSocket 重认证和中断回归；`npm run test:mall` 包含这些源码。依赖门禁新增 `python -m unittest discover -s scripts/ops/tests -p 'test_*.py'`，检查间接高危依赖和不完整扫描报告。均未在本轮执行。

## 阶段报告模板

每阶段记录：新增代码/迁移/契约；测试数量/通过率（本轮填未执行）；指标（未运行）；未完成/风险；下一步。仅在完整验证后把STATUS从“已编写未验证”改为“验收通过”。同一失败最多两轮，记录现象、已尝试步骤及需决策，不盲改。
