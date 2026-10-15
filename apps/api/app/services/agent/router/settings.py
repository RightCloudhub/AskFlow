"""Turn-router confidence bands and version (arch §4.3)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_HIGH_CONFIDENCE = 0.7
DEFAULT_MEDIUM_CONFIDENCE = 0.45
DEFAULT_OPEN_TASK_SCAN_LIMIT = 50


class RouterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    high_confidence: float = Field(
        default=DEFAULT_HIGH_CONFIDENCE, ge=0, le=1, validation_alias="ROUTER_HIGH_CONFIDENCE"
    )
    medium_confidence: float = Field(
        default=DEFAULT_MEDIUM_CONFIDENCE, ge=0, le=1, validation_alias="ROUTER_MEDIUM_CONFIDENCE"
    )
    version: str = Field(default="2026.10.1", validation_alias="ROUTER_VERSION")
    open_task_scan_limit: int = Field(
        default=DEFAULT_OPEN_TASK_SCAN_LIMIT, ge=1, validation_alias="ROUTER_TASK_SCAN_LIMIT"
    )
