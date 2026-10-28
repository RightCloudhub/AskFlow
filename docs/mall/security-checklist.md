# 商城安全检查清单

状态：M0设计及后续验证清单，**未执行扫描/渗透/自动化验收**，不宣称ASVS认证。位置为计划域，完成状态见STATUS。

| ASVS L2 / API Top10 | 实现与检查位置 | 必须验证 |
|---|---|---|
| V1架构/API9资产管理 | plugins/features、commerce/core、公开最小发现 | 关闭插件无路由/worker/后台旁路；旧profile不变 |
| V2认证/API2 | account、共享auth/security | Argon2id兼容bcrypt；强度/泄露钩子；账号/IP锁定；一致枚举响应/耗时；MFA不可旧登录绕过 |
| V3会话 | account/session、core deps/WS | JWT短寿命/jti；refresh只存hash、轮换/重放整family；设备吊销；Cookie Secure/HttpOnly/Strict+CSRF+Origin |
| V4授权/API1 BOLA/API5 | repositories owner过滤、admin权限依赖 | A查B一律404；没有wallet:adjust403且独立审计；前端隐藏不是安全边界 |
| V5输入/API3属性授权/API8 | Pydantic额外字段拒绝、参数化ORM、上传端口 | 金额strict int；server计价；不能设置owner/role/approval_actor；路径不可控/类型头/大小白名单 |
| V6加密 | account vault、keyed hash、payment HMAC | TOTP/手机静态加密；密码/refresh/恢复码不可逆；独立强密钥生产拒启；常量时间验签 |
| V7日志/错误 | audit masking、trace、core errors | 密码/验证码/refresh/TOTP/完整手机不进日志；后台成功/拒权审计；金融error不泄露异常 |
| V8数据保护 | account export/close、wallet append-only | 停用后无法登录；余额/在办订单阻注销；脱敏订单快照；财务保留不cascade；保留期上线确认 |
| V9通信/API10不安全API | infra resilience、gateway adapter | TLS反代、timeout、限次重试、breaker；unknown资金写先查证；回调金额/币种/商户校验 |
| V10恶意代码/API7 SSRF | 配置白名单、上传/搜索/通知端口 | 不允许客户改外部URL；限制内部connector地址配置权限；无任意代码模板/文件路径 |
| V11业务/API4资源/API6敏感业务 | inventory/order/payment/wallet/referral | 1000抢100；100重复回调；200钱包并发；一键不重复；设备/IP奖励限额/审核 |
| V12文件/API8配置 | local/S3端口、部署 | 文件名随机、拒SVG/HTML执行内容、MAX_UPLOAD_BYTES、静态目录不遍历；非root镜像/最小权限 |
| V13 API | 所有mall/admin/internal接口 | 限流四级429 Retry-After；内部lookup只服务token；游标范围绑定；资源版本409 |
| V14配置 | Settings startup、CI扫描、infra | 多实例memory拒启；弱支付/TOTP/refresh钥拒启；pip-audit/npm audit/bandit新代码门禁 |

## 资金安全专项

- 所有金额整数分+币种，账务API不信客户端total；组合支付/部分退款累计受约束。
- 回调HMAC+时间窗+永久业务流水唯一；同流水不同报文告警；晚付取消清算不复活订单。
- 每journal多posting借贷平衡；快照CAS/非负；财务chain head不分叉；ORM/DB只追加；更正只能冲正。
- 调账申请人与批准人不同，wallet:adjust/wallet:approve、step-up、version；两次批准一条journal。
- 对账四类检查：借贷、快照、哈希、网关；差异持久化/财务通知；发现篡改停止自动资金处理。
- 邀请奖励退款冲正，已花奖励转追偿不扣负；规则版本和防刷信号HMAC留存。

## AskFlow不变量

Harness安全文案/阈值仍为冷代码常量；检索和工具输出为不可信文本，不能授予身份或变更资金；模型只见当前允许能力；所有mall.*写经过Gateway及台账；跨客户订单查询不能用用户文本补造owner mapping。

真实支付商户、外发邮件短信、静态加密密钥轮换、PG容灾、保留政策和ASVS渗透需要部署验收；mock通过不能替代真实生产认证。
