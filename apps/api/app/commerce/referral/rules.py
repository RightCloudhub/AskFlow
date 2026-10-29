"""Registration and first-order rewards are separate delayed, single-level liabilities."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.commerce.admin.settings_service import value
from app.commerce.core.constants import BASIS_POINTS
from app.commerce.core.repository import cas, insert_once
from app.commerce.core.schemas import utc
from app.commerce.referral.models import ReferralReward


async def registered(db, relation):
    amount = await value(db, "mall_referral_registration_cents")
    if not amount:
        return
    expiry = utc(relation.created_at) + timedelta(days=await value(db, "mall_referral_valid_days"))
    await insert_once(db, ReferralReward, values={"user_id": relation.inviter_id,
        "relation_id": relation.id, "kind": "registration", "order_id": None,
        "rule_version": relation.rule_version, "amount_cents": amount,
        "eligible_at": expiry, "expires_at": expiry}, unique=["relation_id", "kind", "rule_version"])


async def completed(db, relation, order):
    now = datetime.now(UTC)
    expiry = utc(relation.created_at) + timedelta(days=await value(db, "mall_referral_valid_days"))
    if expiry <= now:
        return
    due = now + timedelta(days=await value(db, "mall_referral_delay_days"))
    signup = await db.scalar(select(ReferralReward).where(ReferralReward.relation_id == relation.id,
        ReferralReward.kind == "registration").with_for_update())
    if signup is not None and signup.status == "pending" and signup.order_id is None:
        await cas(db, signup, values={"order_id": order["id"], "eligible_at": due, "expires_at": None})
    amount = await value(db, "mall_referral_reward_cents")
    amount += order["total_cents"] * await value(db, "mall_referral_basis_points") // BASIS_POINTS
    if amount:
        await insert_once(db, ReferralReward, values={"user_id": relation.inviter_id,
            "relation_id": relation.id, "order_id": order["id"], "kind": "first_order",
            "rule_version": relation.rule_version, "amount_cents": amount, "eligible_at": due},
            unique=["relation_id", "kind", "rule_version"])
