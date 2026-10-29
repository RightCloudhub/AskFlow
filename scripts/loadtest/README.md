# 商城负载脚本（未运行）

仅用于一次性测试库。先执行迁移、配置 mall profile 和基础设施，再用 `PYTHONPATH=apps/api python scripts/loadtest/seed.py` 预置商品、库存、钱包和凭据。文件默认写 `artifacts/mall-seed.json`、权限 0600；它含令牌，不上传 CI artifacts、不提交 Git，测完按凭据策略销毁。

`k6 run scripts/loadtest/mall-smoke.js` 跑小规模浏览、搜索、加购、下单、mock 回调。`MALL_SCENARIO=detail|search|cart|order|wallet|flash k6 run scripts/loadtest/mall.js` 分场景运行，JSON 摘要写 artifacts。`MALL_VUS` 配置预分配 VU，`MALL_DURATION_SECONDS` 配置普通场景持续秒数；`MALL_RATE` 可覆盖入口速率。

full 的标准目标写在脚本和 `docs/mall/performance.md`。lite 用 `MALL_RATE=300 MALL_SCENARIO=detail` 或 `MALL_RATE=30 MALL_SCENARIO=order`；错误率统计排除限流和已知售罄，但不排除任意 409、401 或 5xx。普通场景另校验 2xx 完成数达到目标，P99 只统计 200。必须同时报告 429、售罄比例、dropped_iterations、业务成交数与数据库不变量；高拒绝率不能当作吞吐达标。正式压测要按模型流量配置 `MALL_RATE_PER_MINUTE`/`MALL_GLOBAL_RATE_PER_MINUTE`，不把默认单 IP 限流造成的拒绝当作系统吞吐。

wallet 场景先生成订单再用余额支付，钱包付款接口单独记录延迟；下单失败或余额耗尽的样本不能算扣款 TPS。秒杀脚本会重复使用账号，适合测限流与去重；要验证真实独立抢购须准备足量独立账号并验证订单/库存数量。不得用入口 queued 响应当作成交。跨机器压测应校时，每轮使用新 fixture，令牌过期前重新预置。

全量硬件基准、唯一买家秒杀与首次实测报告仍需补齐。当前没有实测结果。
