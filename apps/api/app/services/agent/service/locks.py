"""Atomic scoped lease acquisition, renewal and owner-checked release."""

import json
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, or_, select, update

from app.models.service_object_lock import ServiceObjectLock
from app.services.agent.service.inserts import insert_once


def lock_identity(scope, object_key: str) -> str:
    key = json.dumps([scope.organization_id, scope.customer_id, object_key])
    return str(uuid5(NAMESPACE_URL, f"askflow:object-lock:{key}"))


class ObjectLockStore:
    def __init__(self, sessions):
        self.sessions = sessions

    async def acquire(self, scope, object_key: str, *, task_id: str, ttl_seconds: float) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("Object lock TTL must be positive")
        now = datetime.now(UTC)
        until = now + timedelta(seconds=ttl_seconds)
        lock_id = lock_identity(scope, object_key)
        async with self.sessions.begin() as db:
            await insert_once(
                db,
                ServiceObjectLock,
                key="id",
                values={
                    "id": lock_id,
                    "organization_id": scope.organization_id,
                    "customer_id": scope.customer_id,
                    "object_key": object_key,
                    "task_id": task_id,
                    "lease_until": until,
                },
            )
            changed = await db.execute(
                update(ServiceObjectLock)
                .where(
                    ServiceObjectLock.id == lock_id,
                    or_(ServiceObjectLock.lease_until <= now, ServiceObjectLock.task_id == task_id),
                )
                .values(task_id=task_id, lease_until=until)
            )
            return changed.rowcount == 1

    async def holder(self, scope, object_key: str) -> str | None:
        async with self.sessions() as db:
            return await db.scalar(
                select(ServiceObjectLock.task_id).where(
                    ServiceObjectLock.id == lock_identity(scope, object_key),
                    ServiceObjectLock.lease_until > datetime.now(UTC),
                )
            )

    async def release(self, scope, object_key: str, *, task_id: str) -> bool:
        async with self.sessions.begin() as db:
            changed = await db.execute(
                delete(ServiceObjectLock).where(
                    ServiceObjectLock.id == lock_identity(scope, object_key),
                    ServiceObjectLock.task_id == task_id,
                )
            )
            return changed.rowcount == 1
