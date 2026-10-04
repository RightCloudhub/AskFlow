# 首次设置：本地试用

[配置指南](README.md) · 上一篇：[配置基础](basics.md) · 下一篇：[功能](features.md)

本演练在一台计算机上启动 AskFlow 的两个部分。它使用 SQLite、本地上传文件、离线搜索嵌入和抽取式答案。你不需要付费模型连接或 Docker。

命令使用 Linux/macOS 风格的 shell。在 Windows 上，请使用合适的 Linux 环境（如 WSL），或请运维人员进行适配。**终端（terminal）** 是你输入命令的应用程序；每条命令后按 Enter 并等待它完成。

## 1. 获取软件

安装 Git、Python 3.11 或更高版本，以及带 npm 的 Node.js 20。如果你已经有仓库，请在仓库根文件夹中打开终端，而不是再克隆一份。

```bash
git clone https://github.com/RightCloudhub/AskFlow.git
cd AskFlow
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**虚拟环境（virtual environment）** 是本项目 Python 依赖的私有文件夹。`source .venv/bin/activate` 会为当前终端选择它。当你打开新的 API 终端时，请再次运行该激活命令。

## 2. 创建 API 设置文件

如果 `apps/api/.env` 已经存在，请私下检查它并保留其设置，而不是替换它。对于全新安装，请在 `apps/api` 中创建 `.env`，内容如下：

```dotenv
ASKFLOW_ENV=development
SECRET_KEY=REPLACE_WITH_A_GENERATED_SECRET
DATABASE_URL=sqlite+aiosqlite:///./askflow.dev.db
ASKFLOW_PROFILE=full
SERVICE_TASKS_ENABLED=false
```

在本地生成你自己的密钥：

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

将输出粘贴为 `SECRET_KEY` 的值并保存文件。此密钥用于签名登录；它不是你的账号密码。重启时请保持相同的密钥。在 Linux/macOS 上，用以下命令限制文件访问：

```bash
chmod 600 .env
```

此试用明确禁用已保存的后台服务任务，直到你有真实的业务连接可供测试。其他已启用的功能仍可能显示演示或回退行为。你稍后可以使用 [服务运营](service.md) 启用任务。

现在暂时**省略**模型、Redis、Chroma 和 S3 设置。如果你之前遵循了其他设置，请清除先前的 shell 覆盖。复制的示例文件可能包含过时的 URL 建议；在启用模型之前请先阅读 [模型](models.md)。

## 3. 启动后端

仍在 `apps/api` 中，运行：

```bash
uvicorn app.main:app --reload --port 8000
```

让此终端保持运行。在浏览器中打开 `http://localhost:8000/health`。寻找 `status: "ok"` 以及标记为 `up` 的数据库依赖项。`localhost` 表示这台计算机；其他人的计算机无法使用你的 `localhost` 地址访问此试用。

首次启动会创建缺失的数据库表。在这个全新试用上，你不需要运行数据库迁移命令。对于现有数据库，请在升级前阅读 [存储与索引](storage.md)。

## 4. 准备并启动 Web 应用

在仓库根目录打开第二个终端：

```bash
cd apps/web
npm ci
```

对于这个 `full` profile 的试用，创建 `apps/web/.env.local`，内容为这个非机密值：

```dotenv
VITE_ASKFLOW_FEATURES=core,rag,agent,tools,ticket,handoff,knowledge,ops,cost,sla,notify,sso,teams,connectors,launch,analytics,mcp,widget,feishu,wecom,dingtalk,qc
```

这会向界面提供已启用的功能列表。它还能让普通客户账号看到适当的链接，尽管当前的功能发现端点仅限客服使用。它不会授予权限或启用后端功能。更改 profile 时请与后端保持一致；请参见 [功能](features.md)。

启动 Web 应用：

```bash
npm run dev
```

打开终端打印的地址，通常是 `http://localhost:5173`。Web 开发服务器会将 API 请求转发到端口 8000。如果任一程序停止，应用的一部分将停止工作。

## 5. 创建第一个账号并测试知识

1. 在登录页面点击 **没有账号？注册 (No account? Register)**。
2. 输入用户名、电子邮件和密码；点击 **注册并登录 (Register and sign in)**。
3. 在全新的开发数据库中，第一个注册的账号会成为管理员。检查 **Admin → 用户管理 (User management)**。之后的注册是普通用户。
4. 创建一个包含几段已批准信息的小型 `.txt` 文件。
5. 在 **Admin → 知识文档 (Knowledge documents)** 下上传它，等待 **启用 (`active`)** 且分块数量非零。
6. 返回 **用户台 (User workspace)**，创建一个会话，并提出一个由该文件回答的问题。
7. 打开 **查看引用 (View references)**，核实答案使用了预期的段落。

抽取式答案可能会直接引用文档。在没有模型的情况下，这是预期行为。也可能存在内置示例知识；关于示例数据的回复并不证明你自己的内容已被索引。

详细的界面说明请使用 [知识指南](../user-guide/knowledge.md)。如果你无法访问管理页面，数据库可能已经包含一个账号；注册不会仅仅因为你更改了某个设置就提升你为管理员。

## 6. 停止和恢复

在正在运行的每个终端中按 **Ctrl+C** 以停止试用。使用相同的数据库路径和密钥从相同的文件夹重启。你的数据库和上传的源文件会保留在磁盘上。

默认的搜索索引是进程本地的，重启后不会自动从所有已上传文档重建。文档仍可能出现在列表中，而搜索需要维护。在依赖重启持久化之前，请遵循 [存储与索引](storage.md)。

## 迈向共享服务

不要简单地将这个开发服务器作为你的生产设置来共享。请与托管运维人员一起安排公共或内部 HTTPS 地址、生产模式设置、持久化存储、备份、适当的账号开通，以及进程管理器。[账号、访问与托管](access.md) 说明了所需的配置决策。
