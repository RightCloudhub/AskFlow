"""Gateway policy, confirmation and step-up settings (arch §4.4)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CONFIRMATION_TTL_SECONDS = 86_400
DEFAULT_OTP_TTL_SECONDS = 300
DEFAULT_OTP_MAX_ATTEMPTS = 5
DEFAULT_ASSURANCE_TTL_SECONDS = 1_800


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    policy_version: str = Field(default="1", validation_alias="GATEWAY_POLICY_VERSION")
    confirmation_ttl_seconds: int = Field(
        default=DEFAULT_CONFIRMATION_TTL_SECONDS, ge=60, validation_alias="CONFIRMATION_TTL_SECONDS"
    )
    otp_ttl_seconds: int = Field(
        default=DEFAULT_OTP_TTL_SECONDS, ge=30, validation_alias="OTP_TTL_SECONDS"
    )
    otp_max_attempts: int = Field(
        default=DEFAULT_OTP_MAX_ATTEMPTS, ge=1, validation_alias="OTP_MAX_ATTEMPTS"
    )
    assurance_ttl_seconds: int = Field(
        default=DEFAULT_ASSURANCE_TTL_SECONDS, ge=60, validation_alias="ASSURANCE_TTL_SECONDS"
    )
