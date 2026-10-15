"""Channel inbox relay settings (arch §9.1)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BATCH = 10
DEFAULT_POLL_SECONDS = 2.0
DEFAULT_MAX_ATTEMPTS = 5


class ChannelSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    inbox_relay_enabled: bool = Field(default=True, validation_alias="CHANNEL_INBOX_RELAY_ENABLED")
    inbox_batch: int = Field(default=DEFAULT_BATCH, ge=1, validation_alias="CHANNEL_INBOX_BATCH")
    inbox_poll_seconds: float = Field(
        default=DEFAULT_POLL_SECONDS, ge=0.5, validation_alias="CHANNEL_INBOX_POLL_SECONDS"
    )
    inbox_max_attempts: int = Field(
        default=DEFAULT_MAX_ATTEMPTS, ge=1, validation_alias="CHANNEL_INBOX_MAX_ATTEMPTS"
    )
