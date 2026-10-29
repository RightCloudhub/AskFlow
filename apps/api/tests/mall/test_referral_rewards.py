"""Real completed orders release delayed rewards; shared devices and refunds stay bounded."""

import pytest
from sqlalchemy import select

from app.commerce.account.crypto import digest, encrypt
from app.commerce.account.repository import profile_for, security_for
from app.commerce.order.refunds import RefundService
from app.commerce.order.schemas import RefundRequest, Transition
from app.commerce.order.service import OrderService
from app.commerce.payment.schemas import StartPayment
from app.commerce.payment.service import PaymentService
from app.commerce.referral.models import ReferralReward, RiskEvent
from app.commerce.referral.service import ReferralService
from app.commerce.wallet.service import WalletService
from app.core.config import get_settings
from .helpers import place, seed, transaction


async def completed_order(runtime, identity):
    async def complete(db):
        await WalletService(db).credit(identity["user_id"], 1000, key="fund:" + identity["user_id"])
        order = await place(db, identity)
        await PaymentService(db).start(identity["user_id"], StartPayment(order_id=order["id"], method="wallet"))
        for status in ("SHIPPED", "DELIVERED", "COMPLETED"):
            current = await OrderService(db).get(identity["user_id"], order["id"])
            await OrderService(db).advance(identity["user_id"], order["id"], actor_id=identity["user_id"],
                payload=Transition(status=status, expected_version=current["version"]))
        return order

    return await transaction(runtime, complete)


async def bind(runtime, identity, *, code: str, device: str, phone="+8613800000001"):
    async def create(db):
        profile = await profile_for(db, identity["user_id"])
        profile.phone_cipher, profile.phone_hash = encrypt(phone), digest("target:" + phone)
        (await security_for(db, identity["user_id"])).phone_verified = True
        return await ReferralService(db).bind(identity["user_id"], code=code, device=device, ip="192.0.2.1")

    return await transaction(runtime, create)


async def release(runtime, identity, order):
    payload = {"user_id": identity["user_id"], "order_id": order["id"]}
    await transaction(runtime, lambda db: ReferralService(db).completed_order(payload))
    async with runtime.sessions() as db:
        ids = list(await db.scalars(select(ReferralReward.id).where(ReferralReward.order_id == order["id"])))
    for identifier in ids:
        await transaction(runtime, lambda db: ReferralService(db).mature(identifier))


@pytest.mark.asyncio
async def test_registration_and_first_order_rewards_reverse_together(mall_runtime, monkeypatch):
    monkeypatch.setenv("MALL_REFERRAL_DELAY_DAYS", "0")
    monkeypatch.setenv("MALL_REFERRAL_REGISTRATION_CENTS", "10")
    get_settings.cache_clear()
    inviter, invitee = await seed(mall_runtime), await seed(mall_runtime)
    code = await transaction(mall_runtime, lambda db: ReferralService(db).code(inviter["user_id"]))
    await bind(mall_runtime, invitee, code=code["code"], device="one-device")
    async with mall_runtime.sessions() as db:
        pending = await db.scalar(select(ReferralReward))
        assert pending.kind == "registration" and pending.order_id is None and pending.status == "pending"
    order = await completed_order(mall_runtime, invitee)
    await release(mall_runtime, invitee, order)
    await release(mall_runtime, invitee, order)
    async with mall_runtime.sessions() as db:
        assert (await WalletService(db).balance(inviter["user_id"]))["available_cents"] == 110
        assert len(list(await db.scalars(select(ReferralReward)))) == 2

    async def refund(db):
        row = await RefundService(db).request(invitee["user_id"], order_id=order["id"], key="refund-reward",
            payload=RefundRequest(amount_cents=1000, reason="return"))
        await RefundService(db).process(row["id"])
        await ReferralService(db).refund({"order_id": order["id"]})

    await transaction(mall_runtime, refund)
    async with mall_runtime.sessions() as db:
        assert (await WalletService(db).balance(inviter["user_id"]))["available_cents"] == 0
        assert all(row.status == "reversed" for row in await db.scalars(select(ReferralReward)))


@pytest.mark.asyncio
async def test_ten_accounts_on_one_device_only_one_auto_reward(mall_runtime, monkeypatch):
    monkeypatch.setenv("MALL_REFERRAL_DELAY_DAYS", "0")
    get_settings.cache_clear()
    inviter = await seed(mall_runtime)
    invitation = await transaction(mall_runtime, lambda db: ReferralService(db).code(inviter["user_id"]))
    for index in range(10):
        identity = await seed(mall_runtime)
        await bind(mall_runtime, identity, code=invitation["code"], device="shared-device",
                   phone="+861380000" + str(index).zfill(4))
        await release(mall_runtime, identity, await completed_order(mall_runtime, identity))
    async with mall_runtime.sessions() as db:
        rewards = list(await db.scalars(select(ReferralReward)))
        assert sum(row.status == "paid" for row in rewards) == 1
        assert sum(row.status == "review" for row in rewards) == 9
        assert len(list(await db.scalars(select(RiskEvent)))) == 9
