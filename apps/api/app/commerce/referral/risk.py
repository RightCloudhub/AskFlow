"""Hashed device, IP, phone-prefix and verified-provider signals inform review."""

from sqlalchemy import func, select

from app.commerce.account.crypto import digest
from app.commerce.admin.settings_service import value
from app.commerce.core.services import enabled, service
from app.commerce.referral.models import ReferralRelation, ReferralReward

SIGNALS = {
    "device": ("device_hash", "mall_referral_device_limit", "mall_risk_device_score"),
    "ip": ("ip_hash", "mall_referral_ip_limit", "mall_risk_ip_score"),
    "phone": ("phone_segment_hash", "mall_referral_phone_limit", "mall_risk_phone_score"),
    "payer": ("payer_hash", "mall_referral_payer_limit", "mall_risk_payer_score"),
}


async def assess(db, relation, *, reward, recipient):
    phone = (recipient or {}).get("phone", "")
    if phone:
        length = await value(db, "mall_referral_phone_prefix_length")
        relation.phone_segment_hash = digest("phone-segment:" + phone[:length])
    if enabled("payment"):
        relation.payer_hash = await service("payment", db).payer_signal(relation.invitee_id, reward.order_id)
    await db.flush()
    paid = select(ReferralReward.relation_id).where(ReferralReward.status.in_(["paid", "reversed", "receivable"]))
    score, counts = 0, {}
    for signal, (column, threshold, weight) in SIGNALS.items():
        fingerprint = getattr(relation, column)
        if not fingerprint:
            continue
        count = await db.scalar(select(func.count()).select_from(ReferralRelation).where(
            ReferralRelation.id != relation.id, ReferralRelation.id.in_(paid),
            getattr(ReferralRelation, column) == fingerprint))
        counts[signal] = count
        if count >= await value(db, threshold):
            score += await value(db, weight)
    return score, counts
