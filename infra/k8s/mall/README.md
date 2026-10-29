# 商城 Kubernetes 配置（未部署验证）

lite 使用单副本/Recreate/SQLite PVC；full 使用 PostgreSQL 主库和可选副本、Redis、S3/MinIO、Elasticsearch 的已有服务，另含 worker、迁移 Job、HPA、PDB 和 TLS Ingress。依赖全栈本地示例见 `infra/compose/prod`；这里不提供 PostgreSQL 自动故障切换。

在目标 namespace 创建 `mall-secrets`（不要将真实 Secret YAML 加入版本库）。lite 至少提供 `SECRET_KEY`；full 还须提供 `DATABASE_URL`、`DATABASE_READ_URLS`、`REDIS_URL`、`SEARCH_URL`、`S3_ENDPOINT`、`S3_PUBLIC_ENDPOINT`、`S3_ACCESS_KEY`、`S3_SECRET_KEY`、`METRICS_TOKEN`、`PAYMENT_CALLBACK_SECRET`、`MALL_TOTP_KEY`、`MALL_REFRESH_SECRET`、`ORDER_LOOKUP_TOKEN`。生产邮箱/短信需另配供应商，console 不会外发。

替换镜像地址、Ingress 域名和 CORS，再创建 `mall-tls`。先单独创建迁移 Job 并等待成功，再应用 full overlay；API 的启动检查会拒绝旧 schema。迁移 Job 名随迁移版本更新，不能并发运行两个迁移。

HPA 最大值为 8，`INSTANCE_COUNT=8` 是安全检查的保守上界；调整副本上限时同步修改。full 的 `mall-revisions` PVC 需要支持 ReadWriteMany 的存储类，供 API 与索引 worker 共享知识修订文件；lite 将修订文件保存在同一个 SQLite 数据卷。完整备份、限额、存储类与 NetworkPolicy 按集群实际网络配置。内部订单连接器不通过此 Ingress 暴露。

本轮没有执行 `kubectl kustomize` 或部署。验证命令、故障演练和通过标准见 `docs/mall/validation.md`。
