"""Infrastructure fields inherited by the application's single Settings object."""

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

PRESETS = {
    "lite": {
        "cache_backend": "memory", "lock_backend": "memory",
        "rate_limit_backend": "memory", "event_bus": "outbox",
        "search_backend": "sqlite_fts", "object_store": "local",
        "worker_mode": "inprocess", "session_backend": "database",
        "flash_sale_backend": "database",
    },
    "full": {
        "cache_backend": "redis", "lock_backend": "redis",
        "rate_limit_backend": "redis", "event_bus": "redis_streams",
        "search_backend": "elasticsearch", "object_store": "s3",
        "worker_mode": "separate", "session_backend": "redis",
        "flash_sale_backend": "redis",
    },
}
PRESETS["custom"] = {**PRESETS["lite"], "search_backend": "like"}


class InfraSettings(BaseSettings):
    askflow_infra: Literal["full", "lite", "custom"] = "custom"
    cache_backend: Literal["redis", "memory", "off"] | None = None
    lock_backend: Literal["redis", "pg", "memory"] | None = None
    rate_limit_backend: Literal["redis", "memory"] | None = None
    event_bus: Literal["redis_streams", "rabbitmq", "kafka", "outbox"] | None = None
    search_backend: Literal["elasticsearch", "pg_fts", "sqlite_fts", "like"] | None = None
    object_store: Literal["s3", "local"] | None = None
    worker_mode: Literal["separate", "inprocess"] | None = None
    session_backend: Literal["redis", "database"] | None = None
    flash_sale_backend: Literal["redis", "database"] | None = None
    notify_email: Literal["smtp", "console"] = "console"
    notify_sms: str = "console"
    instance_count: int = Field(default=1, ge=1)
    web_concurrency: int = Field(default=1, ge=1)
    database_read_urls: str = ""
    db_pool_size: int = Field(default=20, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_pool_timeout: int = Field(default=30, ge=1)
    db_pool_recycle: int = Field(default=1800, ge=1)
    sqlite_busy_timeout_ms: int = Field(default=5000, ge=1)
    sqlite_wal: bool = True
    cache_max_entries: int = Field(default=2048, ge=1)
    cache_ttl_seconds: int = Field(default=60, ge=1)
    cache_null_ttl_seconds: int = Field(default=5, ge=1)
    cache_jitter_seconds: int = Field(default=10, ge=0)
    lock_ttl_seconds: int = Field(default=30, ge=1)
    lock_shards: int = Field(default=128, ge=1)
    mall_rate_limit_enabled: bool = True
    mall_rate_per_minute: int = Field(default=600, ge=1)
    mall_global_rate_per_minute: int = Field(default=180000, ge=1)
    mall_flash_rate_per_minute: int = Field(default=30, ge=1)
    mall_worker_enabled: bool = True
    mall_worker_poll_seconds: float = Field(default=2.0, gt=0)
    mall_worker_batch: int = Field(default=100, ge=1)
    mall_worker_lease_seconds: int = Field(default=60, ge=1)
    mall_worker_max_attempts: int = Field(default=5, ge=1)
    mall_event_retry_base_seconds: int = Field(default=2, ge=1)
    mall_event_retry_max_seconds: int = Field(default=300, ge=1)
    local_object_dir: str = "./data/mall-objects"
    s3_public_endpoint: str | None = None
    search_url: str | None = None
    rabbitmq_url: str | None = None
    kafka_bootstrap_servers: str | None = None
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "askflow@localhost"
    sms_provider_url: str | None = None
    sms_provider_token: str | None = None
    external_timeout_seconds: float = Field(default=5.0, gt=0)
    external_max_retries: int = Field(default=2, ge=0)
    external_retry_base_seconds: float = Field(default=0.1, gt=0)
    breaker_failures: int = Field(default=5, ge=1)
    breaker_reset_seconds: int = Field(default=30, ge=1)
    otel_enabled: bool = False

    @model_validator(mode="after")
    def resolve_infra_preset(self):
        for name, value in PRESETS[self.askflow_infra].items():
            if getattr(self, name) is None:
                object.__setattr__(self, name, value)
        return self
