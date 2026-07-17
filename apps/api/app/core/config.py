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

    def assert_startup_safe(self) -> None:
        """Refuse to start with weak secrets outside development/test (S-01)."""
        if self.env in {"development", "test"}:
            return
        if self.secret_key in WEAK_SECRETS or len(self.secret_key) < 16:
            raise RuntimeError(
                "Refusing to start: SECRET_KEY is weak/default while "
                f"ASKFLOW_ENV={self.env}. Set a strong SECRET_KEY (S-01)."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
