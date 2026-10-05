# 账号、访问与托管

[配置指南](README.md) · 下一篇：[服务运营](service.md)

网站管理员管理人员和内容。托管运维人员管理服务器、网络地址、凭据和环境。在使安装可供他人使用时，请与该运维人员合作。

## 选择环境模式

| `ASKFLOW_ENV` | 预期用途 | 重要行为 |
| --- | --- | --- |
| `development` | 本地开发/试用 | 除非禁用，否则允许本地注册；第一个账号可能成为管理员；提供交互式 API 文档 |
| `test` | 自动化测试 | 后台循环禁用；不要用作客户服务模式 |
| `staging` | 部署演练 | 类似生产的注册限制、机密检查和隐藏的交互式 API 文档 |
| `production` | 共享的运营服务 | 与 staging 相同的启动保护措施；真实集成仍需验证 |

默认值是 `development`。设置 `production` 不会安装 HTTPS、创建备份、配置外部提供商，也不会使原型集成变得完整。

## 设置登录签名密钥

为 `SECRET_KEY` 使用本地生成的不可预测值；请参见 [首次设置](first-setup.md)。Staging 和生产会拒绝已知的弱默认值以及短于 16 个字符的值。通过该最低检查并不是使用易记密码而不是生成密钥的理由。

为同一安装提供服务的所有实例都应使用预期的共享签名密钥。更改它会使现有的已签名登录失效；预计用户需要重新登录。如果没有提供单独的 `NOTIFY_WEBHOOK_SECRET`，它还会更改通知签名。

`ACCESS_TOKEN_EXPIRE_MINUTES` 对普通令牌默认是 `1440`（24 小时）。`JWT_ALGORITHM` 默认为 `HS256`；除非运维人员要更改认证设计，否则请保留它。微件访客令牌使用单独的固定两小时生命周期，而不是此普通令牌设置。

## 决定账号如何创建

| 设置 | 默认值 | 效果 |
| --- | --- | --- |
| `DISABLE_LOCAL_REGISTER` | `false` | 为 true 时，在所有模式下阻止本地自助注册 |
| `ALLOW_LOCAL_REGISTER` | `false` | 除非上面禁用，否则明确允许 staging/production 中的本地注册 |
| `ALLOW_BOOTSTRAP_ADMIN` | `false` | 在 staging/production 中，允许空用户数据库中第一个注册的账号成为管理员 |

在 development/test 中，第一个用户管理员引导独立于 `ALLOW_BOOTSTRAP_ADMIN` 被允许。在 staging/production 中，允许注册和允许引导这两个标志是分开的：启用引导不会同时开放注册。

要通过本地注册建立**新**生产模式安装的第一个管理员，运维人员可以在设置期间限制网络访问，临时启用两个允许标志，注册预期的账号，验证其管理员角色，然后移除引导权限并决定是否应继续保持自助注册开放。每次环境更改后都要重启。

现有的第一个用户不会因为设置引导标志而被提升。标准用户管理页面无法编辑角色或重置密码。请通过运维人员或公司登录集成来安排现有账号的角色更改；不要重置保留的数据库来重新获得访问权限。

对于账号单独开通的安装：

```dotenv
DISABLE_LOCAL_REGISTER=true
ALLOW_LOCAL_REGISTER=false
ALLOW_BOOTSTRAP_ADMIN=false
```

这些设置阻止注册，而不是现有的用户名/密码登录。在关闭自助注册之前，请确认适当的登录/开通途径可用。

## 配置公司登录

公司登录使用**身份提供商（identity provider）**，即认证你组织用户的服务。向其管理员索取确切的服务方（issuer）和客户端/受众标识符，并约定它将发送哪些角色。

```dotenv
OIDC_ISSUER=https://identity.example.com/realms/company
OIDC_CLIENT_ID=askflow
OIDC_MOCK=false
```

启用 `sso` 功能，重启，并让身份运维人员在 `POST /api/v1/admin/sso/oidc/login` 集成经过验证的 ID 令牌交换。这期望的是已经从提供商处获得的 ID 令牌。标准登录页面没有 SSO 按钮、重定向流程或回调设置向导。仅环境值无法完成浏览器登录。

默认角色映射是 `admin`/`administrator` → 管理员，`agent`/`support` → 客服，`user` → 客户。识别出的最高角色胜出；无法识别的角色变为客户。提供商提供的角色/组可以在登录时更新现有账号的角色。账号匹配当前使用电子邮件，因此在推广之前，请让身份管理员验证声明和匹配。

`OIDC_MOCK=true` 在开发中接受模拟测试身份，在 staging/production 中启动时被禁止。进行真实身份验证时请保持它为 false。

以客户和客服/管理员身份验证登录，包括一个已禁用账号和一个不应具有管理员权限的账号。保留约定的账号恢复途径。

## 将浏览器连接到后端

标准前端在同一网站上调用相对路径 `/api/v1/...`。没有已实现的 `VITE_API_URL` 设置。在开发中，Vite 将 `/api` 和 WebSocket 流量代理到 `127.0.0.1:8000`。

对于托管，请让运维人员提供已构建的 Web 文件，并将 `/api` 路由到 API，包括 WebSocket 升级支持和合适的流式超时。诸如 `/tickets` 的客户端页面路由需要返回 Web 应用。仅首页成功并不能证明对话代理正常工作。

除非前端和代理一起有意更改，否则请保留 `API_PREFIX=/api/v1`。仅更改此设置会破坏标准 Web 请求。后端监听地址/端口是服务器启动参数，例如 Uvicorn 的 `--host` 和 `--port`，而不是 `API_PORT` 变量。Web 开发端口在 Vite 配置中设置，通常是 5173。

## 设置允许的浏览器来源

**来源（origin）** 是浏览器页面运行所在的方案、主机和端口，例如 `https://support.example.com`。CORS 是浏览器的跨来源访问检查；它不是认证系统或防火墙。

```dotenv
CORS_ORIGINS='["https://support.example.com"]'
```

使用实际的页面来源，不带 URL 路径。重启 API。设置加载器要求 JSON 列表语法。默认值包含 `http://localhost:5173` 和 `http://127.0.0.1:5173`。

允许第二个来源不会将前端的相对 API 请求重定向到另一台服务器。运维人员仍然需要合适的代理或前端更改。对于托管的微件，浏览器嵌入策略和 frame 头是额外的托管决策。

## 设置请求限制和监控访问

`RATE_LIMIT_PER_MINUTE=60` 是默认的每 IP HTTP 请求限制。共享网络可能让许多用户位于同一个 IP 后面。请设置一个经过测量的限制并进行测试；这不是按客户的计费或模型支出上限。

`TRUST_PROXY_HEADERS=false` 是默认值。仅当 API 可通过受信任的、控制转发客户端地址头的代理访问时，才将其设为 true。否则调用方可能提供误导性的地址。重启并让运维人员验证用于限流的地址。

`METRICS_TOKEN` 在 staging/production 中可选地使用 `X-Metrics-Token` 头保护 `/metrics`。它在 development/test 中不被强制执行。请相应配置监控采集器，并将监控端点保留在预期的网络上。它不保护 `/health` 或普通 API 路由。

## 生产模式决策示例

这是一个在账号、存储和托管安排好后进行调整的模板，而不是部署后就不管的配方：

```dotenv
ASKFLOW_ENV=production
SECRET_KEY=REPLACE_WITH_A_GENERATED_SECRET
DATABASE_URL=postgresql+asyncpg://askflow:REPLACE_WITH_DATABASE_PASSWORD@db.example.com:5432/askflow
ASKFLOW_PROFILE=full
DISABLE_LOCAL_REGISTER=true
ALLOW_BOOTSTRAP_ADMIN=false
OIDC_MOCK=false
CORS_ORIGINS='["https://support.example.com"]'
TRUST_PROXY_HEADERS=false
METRICS_TOKEN=REPLACE_WITH_A_SEPARATE_MONITORING_SECRET
```

只添加你打算使用的模型、存储、任务和渠道连接。将环境应用到所有相关进程，对齐 Web 功能列表，并完成 [验证](troubleshooting.md)。[部署检查清单](../../deploy/checklists/pilot-integration.md) 包含运维人员进一步的验收工作。
