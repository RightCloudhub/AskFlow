"""Memory read/write settings (arch §4.8)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_TOP_K = 5
DEFAULT_PROMPT_MAX_CHARS = 400


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    extract_enabled: bool = Field(default=True, validation_alias="MEMORY_EXTRACT_ENABLED")
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=20, validation_alias="MEMORY_TOP_K")
    prompt_max_chars: int = Field(
        default=DEFAULT_PROMPT_MAX_CHARS, ge=50, validation_alias="MEMORY_PROMPT_MAX_CHARS"
    )
