"""Metrics are operational hints; the database reconciliation report is authoritative."""

from app.commerce.core.services import enabled
from app.commerce.infra import metrics


async def sample(db):
    from app.services.outbox.observability import commerce_snapshot

    outbox = await commerce_snapshot(db)
    metrics.OUTBOX_BACKLOG.set(outbox["backlog"])
    metrics.CALLBACK_REJECTIONS.set(outbox["callbacks_rejected"])
    for name, count in outbox["events"].items():
        metrics.EVENT_RECORDS.labels(event=name).set(count)
    if enabled("inventory"):
        from app.commerce.inventory.observability import snapshot

        values = await snapshot(db)
        metrics.NEGATIVE_STOCK.set(values["negative_inventory"])
        metrics.FLASH_QUEUE.set(values["flash_queue"])
    if enabled("wallet"):
        from app.commerce.wallet.observability import snapshot

        values = await snapshot(db)
        metrics.UNBALANCED.set(values["unbalanced_journals"])
        metrics.RECONCILIATION_DIFFS.set(values["reconciliation_diffs"])


async def refresh():
    from app.core import database
    from app.plugins.runtime import get_app_context

    ctx = get_app_context()
    if ctx is not None and ctx.enabled("mall_core"):
        async with database.SessionLocal() as db:
            await sample(db)


async def consume(_db, envelope):
    kind = envelope["event_type"]
    if kind.startswith("mall.order."):
        metrics.ORDER_TOTAL.labels(status=kind.rsplit(".", 1)[-1]).inc()
    if kind.startswith("mall.payment."):
        metrics.PAYMENT_TOTAL.labels(status=kind.rsplit(".", 1)[-1]).inc()
