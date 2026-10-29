# 审核后修复与未实施测试

日期：2026-10-30；分支 `feat/mall-platform-completion`；修复基线 `32db6b5`。
用户在独立审核后明确授权修改和运行验证，随后要求列出未实施测试并提交当前修复。本提交是部分修复，不是 FIX-01–FIX-40 全部完成声明。

## 已修改

- FIX-01：认证包延迟导入，保留 `AuthService` 聚合导入兼容；Python 3.12.13 的 `import app.main` 成功。
- FIX-02：未知账号不构造保留域名邮件；手机号用户通过已验证手机找回。发送冷却也返回相同 accepted 结构，处理时间设最低值。手机身份使用非投递标记保留 users 非空唯一约束，真实联系方式仍在扩展表。
- FIX-03/04：15 条原有生产结构违规重构；商城 Ruff 告警清理。`check_mall_metrics.py` 复用未修改的原指标检查实现，输出原始发现、明确例外与逐文件 SHA256；测试结构没有豁免。报告见 `fix-metrics.json`，其中 head 是报告生成时的基线提交，文件摘要可与本提交对应。
- FIX-05：修复 SQLite 下单令牌条件更新被 ORM 在 Python 中比较 naive/aware 时间；实际 HTTP 替代 profile 路由对象枚举。
- FIX-06/07：沙箱内最小线程退出和 SQLite 连接也挂起。沙箱外离线 eval 与 SQLite 升级完成；没有据此臆造迁移或 eval 业务缺陷。PG、降级及旧库升级仍未完成。
- FIX-08：`npm ci` 后前端构建通过；现有 Playwright 依赖锁文件已生成，浏览器尚未启动。
- FIX-09/17：库存尝试与失败 Counter、负库存/秒杀配置缺口 Gauge、回调 accepted/rejected Counter 已接入。告警表达式改为失败率；Prometheus 触发验证未运行。
- FIX-10/37：命令事务记录 ORM 新增/修改/删除、条件更新和幂等插入的实际 before/after，沿用审计遮罩。角色及库存接口已有测试；完整接口审计矩阵和对象存储外部副作用审计仍待验收。
- FIX-11：wallet/referral/管理员身份查询与初始化改走 account 接口，不直接导入其 repository；未完成全仓架构合规矩阵。
- FIX-12：新支付先贷记 deferred_sales；订单首次完成结转 sales；完成前/后退款冲减对应科目。已有资金回归通过，但收入时点专项断言和旧商城财务数据兼容迁移尚未编写。
- FIX-16：商城 `/health` 与 `/health/ready` 返回端口矩阵，live 单独存在；DB/Redis/搜索/对象存储检查有界。真实 SMTP/SMS 标记 unverified，worker 进程和只读副本健康未实际探测，不能认为完整端口健康验收完成。
- FIX-19/27：新增真实 HTTP 邮箱/手机注册、登录、找回、重置与会话吊销；验证码过期/尝试耗尽、找回枚举最低耗时、并发 refresh 家族吊销测试。

## 已运行结果

运行环境为仓库根目录 `.venv` 的 Python 3.12.13，开发/安全/可选商城依赖已安装。涉及 SQLite/线程的运行在获授权的沙箱外进行，数据库和原始报告位于 `/tmp`。

| 验证 | 实际结果与范围 |
|---|---|
| `PYTHONPATH=apps/api ... .venv/bin/python -c 'import app.main'` | 退出 0；原 full profile 可导入 |
| `.venv/bin/ruff check --no-cache apps/api/app/commerce apps/api/tests/mall` | 退出 0 |
| `.venv/bin/python scripts/ops/check_mall_metrics.py` | 生产结构 0，增量阻断 0；不等于全仓存量零违规 |
| 首次完整 pytest | 526 通过、22 失败、44 跳过；失败后修复时间比较和 profile 检查；该轮不能称全绿 |
| 修复后商城已有 suite | 66 通过、44 full 跳过；包含 1000 抢 100、10 次并发同键下单、100 次回调、200 钱包变动、ChatTurn/越权/退款/奖励冲正 |
| 新增账号/审计/指标健康测试 | 11 通过、11 full 跳过；找回耗时均值写入该轮 JUnit；不是统计学侧信道认证 |
| 提交前最终完整 pytest | 退出 0；559 通过、55 full/外部环境跳过、2 条警告；耗时 161.19 秒。警告为 Starlette TestClient 弃用与 JUnit record_property 格式兼容提示 |
| 离线 eval | 退出 0；8 通过、0 失败 |
| SQLite `alembic upgrade head` | 退出 0；一次性空库升级到商城修订；没有降级/旧库兼容结论 |
| `npm run build` | 退出 0；tsc 与 Vite 通过；仍有资源块大小提示 |
| 商城覆盖率 | 之前一次商城 suite 为 63%；报告产生在新增测试/最终修改前。未达 85%，资金 95% 未证实 |

最终完整 pytest 包含当前新增测试与旧客服回归；机器摘要见 `fix-verification.json`。原始临时文件不作为跨机器可用的永久证据。

## 已有测试/脚本，但尚未运行

| FIX | 尚未执行的验收 |
|---|---|
| 07、26、34、36 | PostgreSQL/Redis full suite；PG 升降级；SQLite 降级再升级；已有客服库含真实数据的兼容升级；当前提交 CI migration job |
| 08、24、32、36 | 浏览器 Shop/购物/后台冒烟；真正后台页面/权限隐藏 e2e；本机已有 `~/.cache/ms-playwright` 但未启动 |
| 29、36 | bandit、pip-audit、npm audit 独立报告和增量门禁；npm ci 只提示 9 项依赖漏洞（5 moderate、4 high），尚未归因或修复 |
| 30、32 | k6 冒烟和全部正式硬件基准；lite/prod 从零容器部署；k8s 渲染/部署；Prometheus 告警实际触发、Grafana/日志演练 |
| 28 | 最终代码商城/资金覆盖率重新采集及 85%/95% 门禁 |
| 33 | 原 profile 静态清单比较在审核阶段完成；最终完整 pytest 的 HTTP profile 测试可以提供部分行为证据，仍不能替代所有旧客服线上场景 |

## 尚未补齐或编写完整的测试

| FIX | 测试/验收缺口 |
|---|---|
| 19、25 | 全 API 注册→验证→登录→2FA→购物→支付→退款→邀请→客服旅程；API 2FA 登录、双向换绑、注销阻断及历史脱敏；注册/登录枚举耗时矩阵。多数领域 fixture 仍直接建立用户/会话，仅新增账号 suite 使用真实认证流程 |
| 13、20、27 | 邀请关系真正并发绑定与互邀；真实付款关联信号与风控误伤率校准；秒杀故障、worker 租约恢复、Redis/DB 差异修正。并发 refresh 新测试已实现并在 lite 通过 |
| 21、22 | 完整状态机允许/拒绝矩阵；乱序回调与取消/支付真实竞争；超限退款独立审批全流程 |
| 12、23 | 收入确认时点专项测试、旧财务账兼容；篡改后财务通知端到端；人工对账报告与权限审计完整链路 |
| 10、14、24 | 全权限点/角色/API 拒权矩阵、所有后台写接口前后值矩阵；ChatTurn L2 拒绝与超限审批；工单通知 ≤5 秒实测 |
| 15 | 通知 outbox→消费→worker→实际发送的完整投递、失败重试、死信及关闭渠道测试；现有局部消费测试不替代该流程 |
| 16、26、31、35 | 全端口实现/故障矩阵；真实 full 的搜索/S3/worker/限流（fixture 仍覆盖 LIKE/local，关闭后台循环/业务限流）；副本故障、写后读、多实例失效、熔断恢复；不安装 Redis/S3/MQ SDK 的 lite 独立环境 |
| 18、29 | 完整 OpenAPI 生成与契约校验；ASVS 控制编号→实现→运行结果矩阵、secret scan、日志/PII 快照审计 |
| 20、30 | 秒杀压测独立买家与独立 DB 不变量检查；现有脚本按 VU 重用买家，本提交尚未修正；全部性能目标无实测数字 |
| 32、36 | 两档零起点部署及当前提交 CI run/验收工件链接 |

收入确认沿用 ADR005 的订单完成时口径。正式币种/退款邀请/保留政策、通知供应商、真实风控数据及外部验收环境仍需负责人决策。没有推送远端或触发 CI。
