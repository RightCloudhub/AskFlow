# 运营体验优化 · 测试与运维验收（2026-10）

对应需求：[`docs/product/ops-feedback-2026-10.md`](../product/ops-feedback-2026-10.md)（P1–P7）。

## 1. 自动化测试

| 层级 | 文件 | 覆盖 | 命令 |
|------|------|------|------|
| 后端单元 | `apps/api/tests/unit/test_ops_feedback.py` | P1 拒答原因取值与兜底；P2 账号→账户同义改写；P6 中文工单前缀且稳定；P7 近重复判定与跨来源去重 | `cd apps/api && python -m pytest -q tests/unit/test_ops_feedback.py` |
| 后端集成 | `apps/api/tests/integration/test_ops_feedback_api.py` | P3 接管列表/认领返回 `user_name`、`claimed_by_name`；P1 真实拒答落库为 `zero_hit`/`weak_evidence` | `cd apps/api && python -m pytest -q tests/integration/test_ops_feedback_api.py` |
| 前端纯函数 | `apps/web/src/components/admin/ops-labels.test.ts` | P1 缺口原因中文映射（含历史 `skipped`）；P4 等待时长（无时区的 UTC 时间、`Z`、`+08:00` 三种输入）与按钮权限矩阵；P5 业务类型中文 | `cd apps/web && npm run test:ops` |
| 前端类型/构建 | — | 新字段与组件类型检查 | `cd apps/web && npm run build` |
| 全量回归 | — | 原有 400 项不回退 | `cd apps/api && python -m pytest -q` → **408 passed** |

前端测试用 Node 22 自带的 `--experimental-strip-types` 运行，不新增依赖。

## 2. 手工验收（演示环境）

前置：按 `apps/api/README.md#demo-data` 启动 API 并执行 `scripts/seed_demo.py`，前端 `npm run dev`，用 `admin / Admin12345!` 登录。

| 用例 | 步骤 | 预期 | 结果 |
|------|------|------|------|
| TC-1 缺口原因（P1） | 打开「知识缺口」 | 原因列为「证据不足」/「无命中」标签，悬停有处理建议；无 `skipped` | 通过 |
| TC-2 同义词（P2） | 对话台问「账号被锁了怎么办？」 | 命中「账户与安全」作答；「知识缺口」中无此问题 | 通过（缺口由 3 条降为 2 条） |
| TC-3 接管可读性（P3） | 打开「人工接管」 | 显示客户用户名；认领人为本人时显示「我」，他人显示其用户名；页面无 UUID | 通过 |
| TC-4 接管按钮（P4） | 同上；另用第二个坐席账号查看已被认领的行 | 排队行只有「认领」并显示等待时长；本人认领行只有「交还 AI」；他人认领行显示「已被认领」 | 通过 |
| TC-5 工单动作（P5） | 打开「工单中心」 | 待处理：处理中 + 标记解决；处理中：仅标记解决；已解决：「无需操作」；类型列全中文 | 通过 |
| TC-6 工单标题（P6） | 对话台发「商品质量太差了，我要投诉」 | 回复与工单标题为「【投诉】…」 | 通过 |
| TC-7 回答去重（P7） | 对话台问「退款多久能到账？」 | 「3-5 个工作日原路返回」只出现一次 | 通过 |

## 3. 发布与运维说明

- **数据库**：无表结构变更。`HandoffOut` 新增两个可空字段，向后兼容；旧客户端忽略即可。
- **配置**：同义词随 `data/samples/query_synonyms.yaml` 发布；自定义了 `REWRITE_SYNONYM_PATH` 的环境需手动合入 `account` 组，否则 TC-2 不生效。
- **性能**：接管列表增加一次按 ID 批量查询用户名（`IN` 查询，无 N+1）。
- **兼容**：
  - 历史缺口的 reason 仍为 `skipped`，前端显示「未记录原因」，不回填。
  - 旧的 `[complaint]` 前缀工单不改名。工单按标题合并，所以升级当时仍开放的同题工单不会与新建的「【投诉】…」工单合并，可能出现一次重复。
- **行为变化**：知识缺口记录失败不再被静默吞掉，会随当前事务报错并进日志。上线后请关注 `GapService.record` 相关异常（预期为 0）。
- **回滚**：纯代码回滚即可，无数据迁移；回滚后新缺口的 reason 会重新变为 `skipped`。

## 4. 已知限制

- 等待时长在页面上每 15 秒随列表刷新，不是秒级实时。
- 根因：SQLite 返回不带时区的 UTC 时间。前端已按 UTC 解析；全局修复（后端统一输出带时区的 ISO 时间）已列入 `docs/engineering/backend-plan.md`。
