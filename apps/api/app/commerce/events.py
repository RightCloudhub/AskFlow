"""Local transactional consumers plus optional broker publication."""

from datetime import UTC, datetime

from app.commerce.core.models import EventConsumerReceipt
from app.commerce.core.repository import insert_once
from app.commerce.core.services import enabled
from app.commerce.infra.runtime import infra


async def dispatch(db, event):
    envelope = event.payload
    handlers = _handlers(envelope["event_type"])
    for name, handler in handlers:
        claimed = await insert_once(db, EventConsumerReceipt, values={"event_id": envelope["event_id"],
            "consumer": name, "processed_at": datetime.now(UTC)}, unique=["event_id", "consumer"])
        if claimed:
            await handler(db, envelope)
    await infra().bus.publish(envelope)


def _handlers(event_type):
    from app.commerce.observability import consume

    handlers = [("metrics", consume)]
    if event_type == "mall.settings.changed":
        handlers.append(("settings", _settings))
    if enabled("notify"):
        handlers.append(("notifications", _notify))
    if enabled("referral") and event_type in {"mall.order.completed", "mall.refund.settled"}:
        handlers.append(("referrals", _referral))
    if enabled("catalog") and event_type == "mall.catalog.changed":
        handlers.append(("catalog", _catalog))
    return handlers


async def _settings(_db, envelope):
    from app.plugins.runtime import require_app_context

    cache = require_app_context().services.get("mall_setting_cache", {})
    cache.pop(envelope["payload"]["key"], None)


async def _notify(db, envelope):
    from app.commerce.notify.service import NotificationService

    await NotificationService(db).consume(envelope)
    payload = envelope.get("payload", {})
    if payload.get("requires_review") or payload.get("differences", 0):
        from app.commerce.admin.permissions import recipients

        for user_id in await recipients(db, "finance:reconcile"):
            await NotificationService(db).consume({**envelope, "payload": {**payload, "user_id": user_id}})


async def _referral(db, envelope):
    from app.commerce.referral.service import ReferralService

    service = ReferralService(db)
    handler = service.completed_order if envelope["event_type"] == "mall.order.completed" else service.refund
    await handler(envelope["payload"])


async def _catalog(db, envelope):
    from app.commerce.catalog.index import synchronize

    await synchronize(db, envelope["payload"]["spu_id"])
