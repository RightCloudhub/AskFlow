# 存储与索引

[配置指南](README.md) · 下一篇：[账号、访问与托管](access.md)

AskFlow 将多种数据保存在不同的地方。仅备份数据库并不包括上传的文档文件或每个搜索索引。

## 了解必须保留的内容

除非你配置了绝对路径，否则下面的路径相对于 API 的工作目录。

| 数据 | 默认位置 | 它包含什么 |
| --- | --- | --- |
| 数据库 | `./askflow.dev.db` | 账号、消息、工单、文档元数据、任务、偏好和其他记录 |
| 上传的来源 | `./data/uploads` | 文档源文件正文，包括已发布的知识草稿 |
| 修订快照 | `./data/revisions` | 用于比较和回滚的文档版本 |
| 关键字和默认向量索引 | 进程内存 | 为搜索准备的数据；进程停止时丢失 |
| 可选的 Chroma 数据 | 配置的目录或 Chroma 服务器 | 持久化向量搜索数据 |

当前启动不会从所有已存储的源重建完整的内存文档索引。重启后，文档在数据库中可能仍显示为 `active`，但需要重建索引才能恢复完整的搜索行为。内置示例仍可能可搜索，从而掩盖这一区别。

请一起持久化数据库、上传文件、修订和已配置的 Chroma 存储。请让运维人员安排一致的备份和一次恢复演练。在容器中，位于一次性容器内的目录不是持久化存储方案；请挂载适当的卷。

## 小型试用使用 SQLite

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./askflow.dev.db
```

这会在工作目录中创建或使用该文件。Linux 绝对路径使用四个斜杠：

```dotenv
DATABASE_URL=sqlite+aiosqlite:////srv/askflow/data/askflow.db
```

在启动前创建父目录并授予 API 账号访问权限。请始终从预期的文件夹启动程序。路径输入错误可能会创建一个不同的空数据库，使其看起来像所有用户都消失了。

## 连接 PostgreSQL

PostgreSQL 是一个独立的数据库服务。向其管理员索取主机、端口、数据库名称、用户名、密码以及任何所需的传输安全选项。

```dotenv
DATABASE_URL=postgresql+asyncpg://askflow:REPLACE_WITH_DATABASE_PASSWORD@db.example.com:5432/askflow
```

前缀必须包含异步驱动，即 `postgresql+asyncpg`。含 URL 特殊字符的凭据需要正确的 URL 编码；请让数据库运维人员提供格式正确的连接字符串。

**仅用于本地开发依赖**，仓库提供了 Docker Compose。从仓库根目录：

```bash
docker compose -f infra/compose/dev/docker-compose.yml up -d postgres redis
```

对于直接运行在同一台计算机上的 API，开发数据库 URL 为：

```dotenv
DATABASE_URL=postgresql+asyncpg://askflow:askflow@localhost:5432/askflow
```

捆绑的用户名/密码是开发值。Compose 文件启动的是依赖项，不是 AskFlow API 或 Web 应用。它暴露主机端口，不是生产部署模板。

更改 `DATABASE_URL` 只是选择一个数据库；它不会传输记录。在切换现有服务之前，请让运维人员迁移并验证记录。之后恢复旧 URL 也不会把在新数据库中创建的记录复制回来。

## 设置修订存储和上传大小

```dotenv
REVISION_STORE_DIR=/srv/askflow/data/revisions
MAX_UPLOAD_BYTES=15728640
```

上传限制默认为 15 MiB。它计的是文件字节数，不是页数或字符数。前端和任何反向代理可能有各自的上传限制；最小的适用限制生效。

更改 `REVISION_STORE_DIR` 不会移动旧的快照。在切换之前，请通过运维人员复制或迁移保留的数据。上传源存储仍硬编码为 `./data/uploads`（针对标准适配器）；没有 `UPLOAD_DIR` 环境设置。

## 理解 S3 设置

`S3_ENDPOINT`、`S3_ACCESS_KEY`、`S3_SECRET_KEY` 和 `S3_BUCKET` 已定义，但标准上传适配器不使用它们。设置它们或启动捆绑的 MinIO 容器**不会**将上传或备份迁移到对象存储。

请为实际的上传目录使用持久的本地/共享存储。采用对象存储目前需要开发者进行适配器集成工作。不要基于文件已被复制到 S3 的假设而删除本地文件。

## 使用 Chroma 添加持久化向量搜索

首先在 API 虚拟环境中安装可选依赖，从 `apps/api` 执行：

```bash
pip install -e ".[vector]"
```

选择以下配置之一。

**本地持久化目录：**

```dotenv
CHROMA_PERSIST_DIR=/srv/askflow/data/chroma
CHROMA_COLLECTION=askflow
```

**Chroma 服务器：**

```dotenv
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_COLLECTION=askflow
```

对于那个本地服务器示例，请从仓库根目录启动仓库的 Chroma 服务：

```bash
docker compose -f infra/compose/dev/docker-compose.yml up -d chroma
```

`CHROMA_HOST` 是主机名，不是包含 `https://` 或路径的 URL。捆绑的主机端口是 8001。如果 API 本身位于同一个 Compose 网络中，服务地址则应改用主机 `chroma` 及其内部端口 `8000`。同样，容器内的 `localhost` 指的是该容器，而不是你的计算机或另一个服务。

如果同时设置了主机和目录，主机优先。这些设置不暴露任何 Chroma 认证/TLS 配置；请让运维人员安排合适的私有连接，或根据需要调整集成。

重启 API，检查 `/health` 中的向量条目，并为一个已知文档建立索引。验证它在重启后仍可搜索。Chroma 会持久化向量数据，但它不会使进程内的关键字索引变为共享，也不会自动恢复其完整内容。

Chroma 初始化或写入失败可能会回退到内存。请检查健康详情和日志，而不要仅凭一次成功的上传就假设已持久化。模型或维度变化需要兼容的集合和完整的重建索引。

## 在后台运行索引

默认情况下，上传在请求期间建立索引。对于异步处理：

```dotenv
INDEX_ASYNC=true
INDEX_WORKER_ENABLED=true
INDEX_WORKER_POLL_SECONDS=1
REDIS_URL=redis://localhost:6379/0
INDEX_QUEUE_KEY=askflow:index_jobs
```

**worker** 是执行排队工作的后台循环。启用后，API 会启动其内置的索引 worker，测试模式除外。上传可以在文档仍处于待处理状态时返回；请刷新文档列表直到处理完成。

没有 Redis 时，索引队列是进程本地的，重启时可能丢失。使用 Redis 时，实现也会保留一份本地副本，并在 Redis 失败时回退到本地；这不是有保证的恰好一次持久作业系统。在启用异步上传的同时禁用 worker 需要另一个合适的消费者，否则排队的工作会一直处于待处理状态。

Redis 还支持共享取消标记；它不会共享关键字索引、检索缓存，也不会使服务任务持久化。服务任务调度独立使用数据库。

对于单进程试用，除非你需要后台上传，否则请将 `INDEX_ASYNC=false`。对于多进程部署，请让运维人员在增加 worker 数量之前验证所有服务进程之间的索引可见性。

## 为现有文档重建索引

标准浏览器页面没有重建索引按钮。运维人员可以使用经过认证的管理员端点 `POST /api/v1/embedding/reindex/{document_id}`。在本地开发环境中，`/docs` 提供了一个交互式请求表单；[服务运营](service.md#当没有界面时使用管理员-api) 说明了如何使用它。

重建索引会从保留的源重建文档的搜索数据，并创建一个修订。它不同于再上传一个文件，后者会创建另一份文档。在更改嵌入方法、恢复内存索引或构建新集合时，请为每个相关源重建索引，然后测试有代表性的问题。

## 升级现有数据库

在升级保留的数据库之前，请先停止并与运维人员一起规划。启动时的缺失表创建和 Alembic 迁移历史是两种不同的机制；在启动已创建的表上盲目运行迁移可能会因“表已存在”而失败。

对于已由 Alembic 正确跟踪的部署，运维人员在正确的环境中从 `apps/api` 检查当前修订并应用升级：

```bash
python -m alembic current
python -m alembic upgrade head
```

这些不是用于初始化每个全新试用或修复未知迁移状态的说明。在标记（stamp）或升级未跟踪的数据库之前，请让运维人员将保留的 schema 与迁移历史进行比较。请参见 [数据库升级说明](../../apps/api/README.md#database-upgrades)。
