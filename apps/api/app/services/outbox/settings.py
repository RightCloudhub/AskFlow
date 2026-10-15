"""Outbox relay settings (arch §4.5)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BATCH = 20
DEFAULT_POLL_SECONDS = 2.0
DEFAULT_MAX_ATTEMPTS = 5


class OutboxSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="OUTBOX_RELAY_ENABLED")
    batch: int = Field(default=DEFAULT_BATCH, ge=1, validation_alias="OUTBOX_RELAY_BATCH")
    poll_seconds: float = Field(
        default=DEFAULT_POLL_SECONDS, ge=0.5, validation_alias="OUTBOX_RELAY_POLL_SECONDS"
    )
    max_attempts: int = Field(
        default=DEFAULT_MAX_ATTEMPTS, ge=1, validation_alias="OUTBOX_RELAY_MAX_ATTEMPTS"
    )
