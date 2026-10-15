"""Persistent dispatch leases; competing workers only claim each due task once."""

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, select, update

from app.middleware.metrics import TASK_LEASE_RECLAIMED_TOTAL, TASKS_DEAD_LETTER_TOTAL
from app.models.service_dispatch import ServiceDispatch

DISPATCH_BATCH_SIZE = 20
LEASE_SECONDS = 300
MAX_DISPATCH_FAILURES = 3
FAILURE_RETRY_BASE_SECONDS = 5
FAILURE_RETRY_MAX_SECONDS = 60
FAILURE_JITTER_RATIO = 0.2


def retry_delay_seconds(attempts: int) -> float:
    """Exponential backoff with jitter (arch §4.5)."""
    delay = min(
        FAILURE_RETRY_BASE_SECONDS * (2 ** max(0, attempts - 1)), FAILURE_RETRY_MAX_SECONDS
    )
    return delay + random.uniform(0, delay * FAILURE_JITTER_RATIO)


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
            reclaimed = await db.scalar(
                select(ServiceDispatch.task_id).where(
                    ServiceDispatch.task_id == task_id,
                    ServiceDispatch.lease_until.is_not(None),
                    ServiceDispatch.lease_until <= now,
                )
            )
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
            if reclaimed is not None:
                TASK_LEASE_RECLAIMED_TOTAL.inc()
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
        if claim.attempts >= MAX_DISPATCH_FAILURES:
            due = None
            TASKS_DEAD_LETTER_TOTAL.inc()
        else:
            due = datetime.now(UTC) + timedelta(seconds=retry_delay_seconds(claim.attempts))
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
