"""Strict shared schemas and UTC representations."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.commerce.core.constants import MAX_SAFE_CENTS

Cents = Annotated[int, Field(strict=True, ge=0, le=MAX_SAFE_CENTS)]
PositiveCents = Annotated[int, Field(strict=True, gt=0, le=MAX_SAFE_CENTS)]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Versioned(Schema):
    expected_version: int = Field(ge=0, strict=True)


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def view(row, fields: tuple[str, ...]) -> dict:
    result = {}
    for field in fields:
        value = getattr(row, field)
        result[field] = utc(value).isoformat() if isinstance(value, datetime) else value
    return result
