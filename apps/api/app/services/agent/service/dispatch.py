"""Persistent dispatch leases; competing workers only claim each due task once."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, select, update

from app.models.service_dispatch import ServiceDispatch

DISPATCH_BATCH_SIZE = 20
LEASE_SECONDS = 300
MAX_DISPATCH_FAILURES = 3
FAILURE_RETRY_SECONDS = 5


@dataclass(frozen=True)
class Claim:
    task_id: str
    token: str
    attempts: int


class DispatchQueue:
    def __init__(self, sessions):
        self.sessions = sessions

    @staticmethod
    def eligible(now):
        return (
            ServiceDispatch.due_at <= now,
            or_(ServiceDispatch.lease_until.is_(None), ServiceDispatch.lease_until <= now),
        )

    async def due(self) -> list[str]:
        async with self.sessions() as db:
            result = await db.scalars(
                select(ServiceDispatch.task_id)
                .where(
                    *self.eligible(datetime.now(UTC)),
                )
                .order_by(ServiceDispatch.due_at, ServiceDispatch.task_id)
                .limit(DISPATCH_BATCH_SIZE)
            )
            return list(result)

    async def claim(self, task_id: str) -> Claim | None:
        now, token = datetime.now(UTC), str(uuid4())
        async with self.sessions.begin() as db:
            changed = await db.execute(
                update(ServiceDispatch)
                .where(
                    ServiceDispatch.task_id == task_id,
                    *self.eligible(now),
                )
                .values(
                    lease_token=token,
                    lease_until=now + timedelta(seconds=LEASE_SECONDS),
                    attempts=ServiceDispatch.attempts + 1,
                )
            )
            if changed.rowcount != 1:
                return None
            row = await db.get(ServiceDispatch, task_id)
            return Claim(task_id=task_id, token=token, attempts=row.attempts)

    async def reschedule(self, claim: Claim) -> None:
        async with self.sessions.begin() as db:
            await db.execute(
                update(ServiceDispatch)
                .where(
                    ServiceDispatch.task_id == claim.task_id,
                    ServiceDispatch.lease_token == claim.token,
                )
                .values(due_at=datetime.now(UTC), lease_token=None, lease_until=None)
            )

    async def record_failure(self, claim: Claim) -> None:
        due = datetime.now(UTC) + timedelta(seconds=FAILURE_RETRY_SECONDS)
        if claim.attempts >= MAX_DISPATCH_FAILURES:
            due = None
        async with self.sessions.begin() as db:
            await db.execute(
                update(ServiceDispatch)
                .where(
                    ServiceDispatch.task_id == claim.task_id,
                    ServiceDispatch.lease_token == claim.token,
                )
                .values(
                    due_at=due, lease_token=None, lease_until=None, last_error="dispatch_failure"
                )
            )
