"""Database leases serialize worker batches across processes and recover after crashes."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import update

from app.commerce.core.models import WorkerLease
from app.commerce.core.repository import insert_once
from app.core.config import get_settings


async def claim(db, key: str):
    now, owner = datetime.now(UTC), str(uuid4())
    await insert_once(db, WorkerLease, values={"key": key, "owner": "",
        "expires_at": now - timedelta(seconds=1)}, unique=["key"])
    result = await db.execute(update(WorkerLease).where(WorkerLease.key == key,
        WorkerLease.expires_at <= now).values(owner=owner, fence=WorkerLease.fence + 1,
            version=WorkerLease.version + 1,
            expires_at=now + timedelta(seconds=get_settings().mall_worker_lease_seconds)))
    return owner if result.rowcount == 1 else None


async def release(db, key: str, owner: str):
    await db.execute(update(WorkerLease).where(WorkerLease.key == key, WorkerLease.owner == owner)
        .values(expires_at=datetime.now(UTC)))
