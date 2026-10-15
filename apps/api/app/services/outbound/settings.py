"""Outbound delivery settings (arch §4.1)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BASE_SECONDS = 2.0
DEFAULT_RATE_PER_MINUTE = 60
DEFAULT_TEXT_LIMIT = 4000


class OutboundSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    max_attempts: int = Field(default=DEFAULT_MAX_ATTEMPTS, ge=1, validation_alias="OUTBOUND_MAX_ATTEMPTS")
    retry_base_seconds: float = Field(
        default=DEFAULT_RETRY_BASE_SECONDS, ge=0.1, validation_alias="OUTBOUND_RETRY_BASE_SECONDS"
    )
    rate_per_minute: int = Field(
        default=DEFAULT_RATE_PER_MINUTE, ge=1, validation_alias="OUTBOUND_RATE_PER_MINUTE"
    )
    default_text_limit: int = Field(
        default=DEFAULT_TEXT_LIMIT, ge=100, validation_alias="OUTBOUND_TEXT_LIMIT"
    )
