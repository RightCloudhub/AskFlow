"""Verified facts with scoped CAS writes, expiry and value-free tombstones."""

import re
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import AwareDatetime, Field, StrictBool
from sqlalchemy import select

from app.models.agent_memory import AgentMemory
from app.services.agent.memory.contracts import DEFAULT_RETENTION_DAYS
from app.services.agent.memory.records import (
    active_records,
    identity,
    insert_record,
    memory_scope,
    record_values,
    update_record,
    utc,
)
from app.services.agent.memory.store import MemoryConflict
from app.services.agent.service.contracts import Record

MAX_FACT_KEY_LENGTH = 255
MAX_FACT_VALUE_LENGTH = 2000
SECRET_KEYS = re.compile(
    r"password|secret|token|credential|card_number|cvv|pin_code", re.IGNORECASE
)
SECRET_DIGITS = re.compile(r"(?:\d[ -]?){13,19}")
SENSITIVE_KEYS = re.compile(r"refund|account|payment|balance|entitlement|credit", re.IGNORECASE)


class MemoryRejected(ValueError):
    """The candidate did not pass the application verification gate."""


class FactCandidate(Record):
    key: str = Field(min_length=1, max_length=MAX_FACT_KEY_LENGTH)
    value: str = Field(min_length=1, max_length=MAX_FACT_VALUE_LENGTH)
    source: Literal[
        "customer_stated", "customer_confirmed", "system_observed", "model_inferred", "staff"
    ]
    confirmed: StrictBool = False
    receipt_ref: str | None = None
    valid_until: AwareDatetime | None = None


class FactView(Record):
    memory_id: str
    key: str
    value: str | None
    version: int
    status: Literal["active", "expired", "deleted"]
    source: str
    verification: str
    verified_at: AwareDatetime
    expires_at: AwareDatetime


def verification(candidate: FactCandidate) -> str:
    if SECRET_KEYS.search(candidate.key) or SECRET_DIGITS.search(candidate.value):
        raise MemoryRejected("Credentials and payment secrets cannot be retained")
    if candidate.source == "model_inferred":
        raise MemoryRejected("Model-inferred facts must be confirmed")
    if SENSITIVE_KEYS.search(candidate.key) and not candidate.confirmed:
        raise MemoryRejected("Financial and entitlement facts require explicit confirmation")
    if candidate.source == "system_observed":
        if not candidate.receipt_ref:
            raise MemoryRejected("System facts require a receipt reference")
        return "observed"
    if not candidate.confirmed:
        raise MemoryRejected("Customer facts require explicit confirmation")
    return "confirmed"


def fact_view(row: AgentMemory) -> FactView:
    expiry = utc(row.expires_at)
    state = "active" if expiry > datetime.now(UTC) else "expired"
    if row.value is None:
        state = "deleted"
    return FactView(
        memory_id=row.id,
        key=row.key,
        value=row.value if state == "active" else None,
        version=row.version,
        status=state,
        source=row.source,
        verification=row.verification,
        verified_at=utc(row.verified_at),
        expires_at=expiry,
    )


class FactStore:
    def __init__(self, sessions):
        self.sessions = sessions

    async def list(self, scope) -> list[FactView]:
        return [fact_view(row) for row in await active_records(self.sessions, scope, kind="fact")]

    async def get(self, scope, key: str) -> FactView | None:
        async with self.sessions() as db:
            row = await db.get(AgentMemory, identity(scope, "fact", key))
            return fact_view(row) if row else None

    async def remember(self, scope, candidate: FactCandidate, *, expected_version: int = 0):
        candidate = FactCandidate.model_validate(candidate.model_dump())
        verified = verification(candidate)
        now = datetime.now(UTC)
        expiry = candidate.valid_until or now + timedelta(days=DEFAULT_RETENTION_DAYS)
        values = {
            "value": candidate.value,
            "source": candidate.source,
            "verification": verified,
            "payload": {"receipt_ref": candidate.receipt_ref},
            "verified_at": now,
            "expires_at": expiry,
        }
        memory_id = identity(scope, "fact", candidate.key)
        async with self.sessions.begin() as db:
            if expected_version == 0:
                inserted = await insert_record(
                    db, record_values(scope, kind="fact", key=candidate.key, values=values)
                )
                if not inserted:
                    raise MemoryConflict("Memory already exists; supply its current version")
            else:
                await update_record(db, memory_id, expected_version=expected_version, values=values)
            return fact_view(await db.get(AgentMemory, memory_id))

    async def delete(self, scope, key: str, *, expected_version: int) -> FactView:
        memory_id = identity(scope, "fact", key)
        async with self.sessions.begin() as db:
            await update_record(
                db,
                memory_id,
                expected_version=expected_version,
                values={"value": None, "payload": {}, "expires_at": datetime.now(UTC)},
            )
            await self._erase_derived(db, scope, key=key)
            return fact_view(await db.get(AgentMemory, memory_id))

    @staticmethod
    async def _erase_derived(db, scope, *, key: str) -> None:
        rows = await db.scalars(select(AgentMemory).where(*memory_scope(scope, kind="experience")))
        for row in rows:
            if key in row.payload.get("conditions", {}):
                row.value, row.payload = None, {}
                row.version += 1
                row.expires_at = datetime.now(UTC)
