"""Deliveries honor preference/quiet hours and persist bounded retries."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.commerce.account.contacts import contact
from app.commerce.admin.settings_service import value
from app.commerce.infra.runtime import infra
from app.commerce.notify.models import Notification, NotificationDelivery, NotificationPreference
from app.core.config import get_settings

SECONDS_PER_HOUR = 3600


def quiet(pref, now) -> bool:
    if pref is None or pref.quiet_start < 0 or pref.quiet_end < 0:
        return False
    hour = now.astimezone(ZoneInfo(pref.timezone)).hour
    if pref.quiet_start <= pref.quiet_end:
        return pref.quiet_start <= hour < pref.quiet_end
    return hour >= pref.quiet_start or hour < pref.quiet_end


async def deliver(db, row):
    notification = await db.get(Notification, row.notification_id)
    pref = await db.scalar(select(NotificationPreference).where(
        NotificationPreference.user_id == notification.user_id,
        NotificationPreference.event_type == notification.event_type,
        NotificationPreference.channel == row.channel))
    if pref is not None and not pref.enabled:
        row.status = "suppressed"
        return
    now = datetime.now(UTC)
    if quiet(pref, now):
        row.next_attempt_at = now + timedelta(hours=1)
        return
    contact_data = await contact(db, notification.user_id)
    target = (contact_data or {}).get("email" if row.channel == "email" else "phone")
    if not target:
        row.status = "suppressed"
        return
    allowed = await infra().limits.allow("notify:" + notification.user_id,
        limit=await value(db, "mall_notification_rate_per_hour"), window=SECONDS_PER_HOUR)
    if not allowed:
        row.next_attempt_at = now + timedelta(hours=1)
        return
    await _send(row, notification, target=target)


async def _send(row, notification, *, target):
    sender = infra().email if row.channel == "email" else infra().sms
    row.attempts += 1
    try:
        row.provider_ref = await sender.send(target=target, subject=notification.subject, body=notification.body)
        row.status, row.last_error = "sent", ""
    except Exception as exc:
        settings = get_settings()
        row.status = "dead" if row.attempts >= settings.mall_worker_max_attempts else "retry"
        row.last_error = type(exc).__name__
        row.next_attempt_at = datetime.now(UTC) + timedelta(
            seconds=settings.external_retry_base_seconds * (2 ** row.attempts))
