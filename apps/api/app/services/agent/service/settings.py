"""Settings for the chat-to-task integration, kept separate from legacy settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_POLL_SECONDS = 5.0


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="SERVICE_TASKS_ENABLED")
    poll_seconds: float = Field(default=DEFAULT_POLL_SECONDS, ge=1,
                                validation_alias="SERVICE_TASK_POLL_SECONDS")
