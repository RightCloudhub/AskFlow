"""UTC daily reconciliation runs once under a durable database lease."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.commerce.core.leases import claim, release
from app.commerce.wallet.operations_models import ReconciliationRun
from app.commerce.wallet.reconcile import reconcile


async def daily(db):
    day = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    key = "mall:reconciliation:" + day
    owner = await claim(db, key)
    if owner is None:
        return None
    prior = await db.scalar(select(ReconciliationRun).where(
        ReconciliationRun.business_date == day,
        ReconciliationRun.kind == "daily",
        ReconciliationRun.status == "completed",
    ).limit(1))
    result = {"id": prior.id, **prior.summary} if prior else await reconcile(db, business_date=day)
    await release(db, key, owner)
    return result
