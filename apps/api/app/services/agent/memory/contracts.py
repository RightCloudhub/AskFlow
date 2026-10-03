"""Finite preference vocabulary prevents free-text instructions and secrets being retained."""

from typing import Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from app.services.agent.service.contracts import Record
from app.services.agent.identity import DEPLOYMENT_SCOPE as DEPLOYMENT_SCOPE

MAX_RETENTION_DAYS = 90
DEFAULT_RETENTION_DAYS = 30
MAX_PREFERENCE_VALUE_LENGTH = 32
PreferenceKey = Literal["language", "response_detail", "contact_channel"]
ALLOWED_VALUES = {
    "language": frozenset({"zh-CN", "en"}),
    "response_detail": frozenset({"brief", "detailed"}),
    "contact_channel": frozenset({"chat", "email"}),
}


class PreferenceChange(Record):
    key: PreferenceKey
    value: str = Field(max_length=MAX_PREFERENCE_VALUE_LENGTH)
    consent: StrictBool
    expected_version: int = Field(ge=0, strict=True)
    retention_days: int = Field(default=DEFAULT_RETENTION_DAYS, ge=1,
                                le=MAX_RETENTION_DAYS, strict=True)

    @model_validator(mode="after")
    def check_value(self):
        if not self.consent:
            raise ValueError("Explicit consent is required")
        if self.value not in ALLOWED_VALUES[self.key]:
            raise ValueError("Unsupported preference value")
        return self


class PreferenceView(Record):
    memory_id: str
    key: PreferenceKey
    value: str | None
    version: int
    status: Literal["active", "expired", "deleted"]
    source: Literal["customer_confirmed"] = "customer_confirmed"
    retention_basis: Literal["explicit_consent"] = "explicit_consent"
    verified_at: AwareDatetime
    expires_at: AwareDatetime
