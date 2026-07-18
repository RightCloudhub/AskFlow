"""Application settings (PRD §3.3, §4.1 S-01 fail-safe)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "change-me-in-production"
WEAK_SECRETS = frozenset(
    {
        DEFAULT_SECRET,
        "secret",
        "changeme",
        "password",
        "askflow",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- runtime ---
    app_name: str = "AskFlow"
    app_version: str = "0.1.0"
    env: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        validation_alias="ASKFLOW_ENV",
    )
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    # --- security ---
    secret_key: str = Field(default=DEFAULT_SECRET, validation_alias="SECRET_KEY")
    access_token_expire_minutes: int = 60 * 24
    jwt_algorithm: str = "HS256"
    rate_limit_per_minute: int = Field(default=60, validation_alias="RATE_LIMIT_PER_MINUTE")

    # --- database / cache ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///./askflow.dev.db",
        validation_alias="DATABASE_URL",
    )
    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")

    # --- object storage ---
    s3_endpoint: str | None = Field(default=None, validation_alias="S3_ENDPOINT")
    s3_access_key: str | None = Field(default=None, validation_alias="S3_ACCESS_KEY")
    s3_secret_key: str | None = Field(default=None, validation_alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="askflow", validation_alias="S3_BUCKET")

    # --- LLM (OpenAI-compatible) ---
    llm_base_url: str | None = Field(default=None, validation_alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, validation_alias="LLM_API_KEY")
    llm_model_classify: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL_CLASSIFY")
    llm_model_rewrite: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL_REWRITE")
    llm_model_generate: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL_GENERATE")
    llm_model_summary: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL_SUMMARY")
    embedding_model: str = Field(default="text-embedding-3-small", validation_alias="EMBEDDING_MODEL")
    embedding_base_url: str | None = Field(default=None, validation_alias="EMBEDDING_BASE_URL")
    embedding_api_key: str | None = Field(default=None, validation_alias="EMBEDDING_API_KEY")
    embedding_dim: int = Field(default=384, validation_alias="EMBEDDING_DIM")
    llm_timeout_seconds: float = Field(default=60.0, validation_alias="LLM_TIMEOUT_SECONDS")

    # --- vector store (Chroma optional) ---
    chroma_persist_dir: str | None = Field(default=None, validation_alias="CHROMA_PERSIST_DIR")
    chroma_host: str | None = Field(default=None, validation_alias="CHROMA_HOST")
    chroma_port: int = Field(default=8001, validation_alias="CHROMA_PORT")
    chroma_collection: str = Field(default="askflow", validation_alias="CHROMA_COLLECTION")

    # --- knowledge index worker ---
    index_async: bool = Field(default=False, validation_alias="INDEX_ASYNC")
    index_worker_enabled: bool = Field(default=True, validation_alias="INDEX_WORKER_ENABLED")
    index_worker_poll_seconds: float = Field(default=1.0, validation_alias="INDEX_WORKER_POLL_SECONDS")
    index_queue_key: str = Field(default="askflow:index_jobs", validation_alias="INDEX_QUEUE_KEY")
    revision_store_dir: str = Field(
        default="./data/revisions",
        validation_alias="REVISION_STORE_DIR",
    )
    cancel_ttl_seconds: int = Field(default=300, validation_alias="CANCEL_TTL_SECONDS")

    # --- tools ---
    order_lookup_url: str | None = Field(default=None, validation_alias="ORDER_LOOKUP_URL")
    order_lookup_token: str | None = Field(default=None, validation_alias="ORDER_LOOKUP_TOKEN")

    # --- RAG / rewrite ---
    rewrite_synonym_path: str = Field(
        default="../../data/samples/query_synonyms.yaml",
        validation_alias="REWRITE_SYNONYM_PATH",
    )
    grounding_threshold: float = 0.35
    grounding_min_hits: int = 1
    grounding_weak_sources: int = 2
    max_question_chars: int = 2000
    max_answer_chars: int = 4000
    max_history_messages: int = 20
    max_history_chars: int = 6000
    # E25 retrieval cache (0 = off)
    retrieval_cache_ttl_seconds: int = Field(
        default=60,
        validation_alias="RETRIEVAL_CACHE_TTL_S",
    )
    retrieval_cache_max_entries: int = Field(
        default=256,
        validation_alias="RETRIEVAL_CACHE_MAX_ENTRIES",
    )
    # E26 mid-session summary compression
    history_summary_threshold: int = Field(
        default=12,
        validation_alias="HISTORY_SUMMARY_THRESHOLD",
    )
    history_summary_keep_recent: int = Field(
        default=4,
        validation_alias="HISTORY_SUMMARY_KEEP_RECENT",
    )

    # --- agent loop budgets (PRD §4.13) ---
    max_loop_steps: int = 6
    max_tool_calls: int = 4
    max_wall_ms: int = 45_000
    max_retries_per_tool: int = 2
    max_slot_turns: int = 3
    intent_clarify_threshold: float = 0.45
    harness_policy_version: str = "1.0.0"

    # --- handoff ---
    handoff_timeout_seconds: int = 300
    # Background handoff timeout + SLA scan (disabled automatically in test)
    sweeper_enabled: bool = Field(default=True, validation_alias="SWEEPER_ENABLED")
    sweeper_interval_seconds: int = Field(default=60, validation_alias="SWEEPER_INTERVAL_SECONDS")
    # Optional shared secret for /metrics in staging/production (header X-Metrics-Token)
    metrics_token: str | None = Field(default=None, validation_alias="METRICS_TOKEN")

    # --- enterprise notify / OIDC / MCP ---
    notify_webhook_url: str | None = Field(default=None, validation_alias="NOTIFY_WEBHOOK_URL")
    notify_webhook_secret: str | None = Field(default=None, validation_alias="NOTIFY_WEBHOOK_SECRET")
    oidc_issuer: str | None = Field(default=None, validation_alias="OIDC_ISSUER")
    oidc_client_id: str | None = Field(default=None, validation_alias="OIDC_CLIENT_ID")
    oidc_mock: bool = Field(default=False, validation_alias="OIDC_MOCK")
    disable_local_register: bool = Field(default=False, validation_alias="DISABLE_LOCAL_REGISTER")
    # Explicit opt-in for local register / first-user admin in staging|production
    allow_local_register: bool = Field(default=False, validation_alias="ALLOW_LOCAL_REGISTER")
    allow_bootstrap_admin: bool = Field(default=False, validation_alias="ALLOW_BOOTSTRAP_ADMIN")
    # Trust X-Forwarded-For for rate limiting only behind a known reverse proxy
    trust_proxy_headers: bool = Field(default=False, validation_alias="TRUST_PROXY_HEADERS")
    max_upload_bytes: int = Field(default=15 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    mcp_enabled: bool = Field(default=False, validation_alias="MCP_ENABLED")
    mcp_tool_whitelist: str = Field(
        default="search_knowledge",
        validation_alias="MCP_TOOL_WHITELIST",
    )
    siem_webhook_url: str | None = Field(default=None, validation_alias="SIEM_WEBHOOK_URL")

    # --- Feishu channel (E7b) ---
    feishu_verification_token: str | None = Field(
        default=None, validation_alias="FEISHU_VERIFICATION_TOKEN"
    )
    feishu_app_id: str | None = Field(default=None, validation_alias="FEISHU_APP_ID")
    feishu_app_secret: str | None = Field(default=None, validation_alias="FEISHU_APP_SECRET")
    # --- WeCom / DingTalk ---
    wecom_token: str | None = Field(default=None, validation_alias="WECOM_TOKEN")
    wecom_corp_id: str | None = Field(default=None, validation_alias="WECOM_CORP_ID")
    wecom_agent_id: str | None = Field(default=None, validation_alias="WECOM_AGENT_ID")
    dingtalk_app_secret: str | None = Field(default=None, validation_alias="DINGTALK_APP_SECRET")
    dingtalk_app_key: str | None = Field(default=None, validation_alias="DINGTALK_APP_KEY")

    # --- multi-bot (E18) ---
    bot_profiles_json: str = Field(default="", validation_alias="BOT_PROFILES_JSON")
    default_bot_id: str = Field(default="default", validation_alias="DEFAULT_BOT_ID")

    # --- i18n (E17) ---
    default_locale: str = Field(default="zh-CN", validation_alias="DEFAULT_LOCALE")

    # --- extended reasoning (E27, default off) ---
    reasoning_enabled: bool = Field(default=False, validation_alias="REASONING_ENABLED")
    reasoning_intent_whitelist: str = Field(
        default="product_faq,troubleshoot",
        validation_alias="REASONING_INTENT_WHITELIST",
    )
    reasoning_max_steps: int = Field(default=2, validation_alias="REASONING_MAX_STEPS")

    # --- sandbox (E28, default off) ---
    sandbox_enabled: bool = Field(default=False, validation_alias="SANDBOX_ENABLED")

    # --- feature plugins (L2) ---
    askflow_profile: str = Field(default="full", validation_alias="ASKFLOW_PROFILE")
    askflow_features: str = Field(default="", validation_alias="ASKFLOW_FEATURES")


    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: object) -> object:
        if isinstance(v, str):
            return [part.strip() for part in v.split(",") if part.strip()]
        return v

    @property
    def is_production_like(self) -> bool:
        return self.env in {"staging", "production"}

    def local_register_allowed(self) -> bool:
        """Dev/test: open unless DISABLE_LOCAL_REGISTER. Prod-like: need ALLOW_LOCAL_REGISTER."""
        if self.disable_local_register:
            return False
        if self.env in {"development", "test"}:
            return True
        return bool(self.allow_local_register)

    def bootstrap_admin_allowed(self) -> bool:
        if self.env in {"development", "test"}:
            return True
        return bool(self.allow_bootstrap_admin)

    def assert_startup_safe(self) -> None:
        """Refuse to start with weak secrets outside development/test (S-01)."""
        if self.env in {"development", "test"}:
            return
        if self.secret_key in WEAK_SECRETS or len(self.secret_key) < 16:
            raise RuntimeError(
                "Refusing to start: SECRET_KEY is weak/default while "
                f"ASKFLOW_ENV={self.env}. Set a strong SECRET_KEY (S-01)."
            )
        if self.oidc_mock:
            raise RuntimeError(
                "Refusing to start: OIDC_MOCK=1 is not allowed when "
                f"ASKFLOW_ENV={self.env}."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
