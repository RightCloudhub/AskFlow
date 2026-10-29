"""Verification delivery is encrypted at rest and retried outside the request path."""

from datetime import UTC, datetime, timedelta

from app.commerce.account.crypto import decrypt
from app.commerce.core.schemas import utc
from app.commerce.infra.errors import dependency_errors
from app.commerce.infra.runtime import infra
from app.core.config import get_settings


async def deliver(db, row):
    if utc(row.expires_at) <= datetime.now(UTC):
        row.delivery_status, row.delivery_cipher = "expired", ""
        return
    sender = infra().email if row.channel == "email" else infra().sms
    row.delivery_attempts += 1
    try:
        await sender.send(target=decrypt(row.target_cipher), subject="AskFlow verification",
                          body=decrypt(row.delivery_cipher))
        row.delivery_status, row.delivery_cipher = "sent", ""
    except dependency_errors():
        settings = get_settings()
        row.delivery_status = "dead" if row.delivery_attempts >= settings.mall_worker_max_attempts else "retry"
        row.delivery_next_at = datetime.now(UTC) + timedelta(
            seconds=settings.external_retry_base_seconds * (2 ** row.delivery_attempts))
