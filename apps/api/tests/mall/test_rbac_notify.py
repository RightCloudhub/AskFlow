"""Backend permission denials and durable notification deduplication."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.commerce.notify.models import Notification
from app.commerce.notify.service import NotificationService
from app.models.audit import AuditLog

from .helpers import headers, seed, transaction


@pytest.mark.asyncio
async def test_wallet_adjustment_without_permission_is_audited(mall_runtime):
    identity = await seed(mall_runtime)
    response = await mall_runtime.client.post("/api/v1/admin/mall/wallet/adjustments", headers=headers(identity),
        json={"user_id": identity["user_id"], "amount_cents": 10, "reason": "test", "step_up_token": "invalid"})
    assert response.status_code == 403
    async with mall_runtime.sessions() as db:
        assert await db.scalar(select(AuditLog).where(AuditLog.action == "mall.permission_denied")) is not None


@pytest.mark.asyncio
async def test_console_notification_still_has_one_inbox_message(mall_runtime):
    identity = await seed(mall_runtime)
    envelope = {"event_id": str(uuid4()), "event_type": "mall.order.paid",
                "payload": {"user_id": identity["user_id"], "order_id": str(uuid4())}}
    for _ in range(2):
        await transaction(mall_runtime, lambda db: NotificationService(db).consume(envelope))
    async with mall_runtime.sessions() as db:
        assert len(list(await db.scalars(select(Notification)))) == 1
