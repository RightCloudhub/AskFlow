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
ASKFLOW_INFRA=full MALL_TEST_DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow_mall_test REDIS_URL=redis://localhost:6379/15 python -m pytest tests/mall -q
```

必须确保 full fixture 真使用 PG/Redis，不能把 full 配置名套到 memory 实现。服务连接失败应失败而非静默 skip。全量旧 pytest/eval 仍保持无LLM、Redis、PG可运行。

| 测试组 | 必须断言 |
|---|---|
| account/security | 邮箱/短信验证TTL/次数/频率；密码重置吊销；refresh旧token重放整family；TOTP/恢复码单用；旧登录/WS/OIDC防MFA绕过；枚举相近耗时/相同响应 |
| profile | mall/mall-lite/mall-only/full/core-only路由；mall-only无Agent/RAG；显式+mall_order依赖闭包；关模块后台也404 |
| catalog/cart | 下架缓存不影响DB拒购；主库重新计价；地址归属/数量范围；游标稳定且无深OFFSET |
| inventory | 1000并发抢100件，准确100订单；可用/预占非负，订单对应；支付/取消/超时抢CAS；两方言 |
| order/idempotency | 同key10并发只有1订单/预占；key改请求409；checkout单用；非法状态409；A查B404 |
| payment/refund | HMAC伪造拒绝；币种/金额/商户比对；100次回调只1journal；同流水异内容冲突；丢回调查单；晚付取消不复活；部分退款总额含pending额度 |
| wallet/reconcile | 200并发扣/充余额正确且非负；每journal借贷等；hash链连续；只追加限制；维护篡改能被对账发现；双人调账不能自批 |
| referral/risk | 同设备10注册奖励限额；关系并发绑定唯一；手机号必须验证；首单/延期/退款冲正；余额不足追偿不扣负；共享IP不直接封禁 |
| support/Gateway | 聊天查真实本人订单；取消确认/L2/库存释放/INTENT→EXECUTED；退款越权拒绝/超限审批；工单/回复outbox≤5秒通知 |
| notify/workers/ports | off邮箱短信仍站内信；event不重复；quiet hours/频控/死信；租约过期/fence；Redis中断安全降级；每端口各实现合约 |

覆盖率整体商城 ≥85%，资金 payment/wallet/refund/referral ≥95%；独立报告资金模块，不能用其他简单模块高覆盖掩盖资金缺口。

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
docker compose -f infra/compose/prod/docker-compose.yml up --build
kubectl kustomize infra/k8s/overlays/lite
kubectl kustomize infra/k8s/overlays/full
```

两档均从注册→验证→订单→mock支付→退款→钱包→邀请→工单走通；检查可关闭端口、readiness和worker。PG主从切换/Redis故障演练独立留证，不以compose有副本当作自动容灾通过。

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

## 阶段报告模板

每阶段记录：新增代码/迁移/契约；测试数量/通过率（本轮填未执行）；指标（未运行）；未完成/风险；下一步。仅在完整验证后把STATUS从“已编写未验证”改为“验收通过”。同一失败最多两轮，记录现象、已尝试步骤及需决策，不盲改。
