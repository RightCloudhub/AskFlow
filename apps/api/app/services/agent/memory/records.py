"""Shared scoped storage and compare-and-swap primitives for memory."""

import json
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.agent_memory import AgentMemory
from app.services.agent.memory.contracts import DEFAULT_RETENTION_DAYS
from app.services.agent.memory.store import MemoryConflict


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def memory_scope(scope, *, kind: str):
    return (
        AgentMemory.organization_id == scope.organization_id,
        AgentMemory.customer_id == scope.customer_id,
        AgentMemory.kind == kind,
    )


def identity(scope, kind: str, key: str) -> str:
    encoded = json.dumps([scope.organization_id, scope.customer_id, kind, key])
    return str(uuid5(NAMESPACE_URL, f"askflow:memory:{encoded}"))


def record_values(scope, *, kind: str, key: str, values: dict) -> dict:
    now = datetime.now(UTC)
    return {
        "id": identity(scope, kind, key),
        "organization_id": scope.organization_id,
        "customer_id": scope.customer_id,
        "kind": kind,
        "key": key,
        "version": 1,
        "verified_at": now,
        "expires_at": now + timedelta(days=DEFAULT_RETENTION_DAYS),
        **values,
    }


async def insert_record(db, values: dict) -> bool:
    insert = {"sqlite": sqlite_insert, "postgresql": postgres_insert}[db.bind.dialect.name]
    changed = await db.execute(
        insert(AgentMemory).values(**values).on_conflict_do_nothing(index_elements=["id"])
    )
    return changed.rowcount == 1


async def update_record(db, memory_id: str, *, expected_version: int, values: dict) -> None:
    changed = await db.execute(
        update(AgentMemory)
        .where(
            AgentMemory.id == memory_id,
            AgentMemory.version == expected_version,
        )
        .values(**values, version=expected_version + 1)
    )
    if changed.rowcount != 1:
        raise MemoryConflict("Memory version changed or does not exist")


async def active_records(sessions, scope, *, kind: str):
    async with sessions() as db:
        rows = await db.scalars(
            select(AgentMemory)
            .where(
                *memory_scope(scope, kind=kind),
                AgentMemory.expires_at > datetime.now(UTC),
                AgentMemory.value.is_not(None),
            )
            .order_by(AgentMemory.verified_at, AgentMemory.id)
        )
        return list(rows)
