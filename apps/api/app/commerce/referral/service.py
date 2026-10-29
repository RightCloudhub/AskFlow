"""Single-level immutable invitations and delayed, reversible rewards."""

import secrets
from datetime import UTC, datetime

from sqlalchemy import func, select, update

from app.commerce.account.contacts import contact
from app.commerce.account.crypto import digest
from app.commerce.account.repository import identity_by_id
from app.commerce.admin.settings_service import value
from app.commerce.core.constants import TOKEN_BYTES
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import cas, insert_once
from app.commerce.core.schemas import utc
from app.commerce.core.services import enabled, service
from app.commerce.referral.models import ReferralCode, ReferralRelation, ReferralReward, RiskEvent
from app.commerce.referral.graph import ensure_acyclic
from app.commerce.referral import risk, rules

DEVICE_RISK_SCORE = 50


class ReferralService:
    def __init__(self, db):
        self.db = db

    async def summary(self):
        return {"risk_events": await self.db.scalar(select(func.count()).select_from(RiskEvent)),
                "risk_pending": await self.db.scalar(select(func.count()).select_from(RiskEvent)
                    .where(RiskEvent.decision == "review"))}

    async def close_user(self, user_id: str):
        await self.db.execute(update(ReferralReward).where(ReferralReward.user_id == user_id,
            ReferralReward.status.in_(["pending", "review"]))
            .values(status="cancelled", version=ReferralReward.version + 1))

    async def code(self, user_id: str):
        await insert_once(self.db, ReferralCode, values={"user_id": user_id,
            "code": secrets.token_urlsafe(TOKEN_BYTES)}, unique=["user_id"])
        row = await self.db.scalar(select(ReferralCode).where(ReferralCode.user_id == user_id))
        return {"code": row.code, "link": "/shop/account?invite=" + row.code}

    async def bind(self, user_id: str, *, code: str, device: str, ip: str):
        invitation = await self.db.scalar(select(ReferralCode).where(ReferralCode.code == code))
        if invitation is None or invitation.user_id == user_id:
            raise MallError("invalid_invitation")
        inviter = await identity_by_id(self.db, invitation.user_id)
        invitee = await identity_by_id(self.db, user_id)
        if inviter is None or invitee is None:
            raise MallError("invalid_invitation")
        await ensure_acyclic(self.db, inviter_id=inviter.id, invitee_id=user_id)
        created = await insert_once(self.db, ReferralRelation, values={"inviter_id": inviter.id,
            "invitee_id": user_id, "code_id": invitation.id, "device_hash": digest("device:" + device),
            "ip_hash": digest("ip:" + ip)}, unique=["invitee_id"])
        row = await self.db.scalar(select(ReferralRelation).where(ReferralRelation.invitee_id == user_id))
        if row.inviter_id != inviter.id:
            raise MallError("invitation_immutable")
        if created:
            await rules.registered(self.db, row)
            await publish(self.db, row, event_type="mall.referral.bound", payload={
                "user_id": inviter.id, "relation_id": row.id})
        return {"id": row.id, "bound": True, "created": created}

    async def completed_order(self, payload):
        if not enabled("order"):
            return
        first = await service("order", self.db).first_completed(payload["user_id"])
        if first is None or first["id"] != payload["order_id"]:
            return
        relation = await self.db.scalar(select(ReferralRelation).where(
            ReferralRelation.invitee_id == payload["user_id"]))
        if relation is None:
            return
        await rules.completed(self.db, relation, first)

    async def mature(self, reward_id: str):
        row = await self.db.get(ReferralReward, reward_id)
        if row is None:
            return
        if row.order_id is None:
            if row.status == "pending" and row.expires_at and utc(row.expires_at) <= datetime.now(UTC):
                await cas(self.db, row, values={"status": "cancelled"})
            return
        relation = await self.db.get(ReferralRelation, row.relation_id)
        order = await service("order", self.db).get(relation.invitee_id, row.order_id, lock=True)
        await self.db.refresh(row)
        if row.status != "pending" or utc(row.eligible_at) > datetime.now(UTC):
            return
        if order["refunded_cents"] or order["status"] != "COMPLETED":
            await cas(self.db, row, values={"status": "cancelled"})
            return
        if not await self._eligible(row, relation):
            await cas(self.db, row, values={"status": "review"})
            return
        journal = await service("wallet", self.db).credit(row.user_id, row.amount_cents,
            key="reward:" + row.id, source="marketing")
        await cas(self.db, row, values={"status": "paid", "journal_id": journal["id"]})
        await publish(self.db, row, event_type="mall.referral.paid", payload={"user_id": row.user_id, "reward_id": row.id})

    async def _eligible(self, reward, relation):
        await service("wallet", self.db).lock()
        recipient = await contact(self.db, relation.invitee_id)
        permitted = bool(recipient and recipient["phone_verified"])
        score, signals = await risk.assess(self.db, relation, reward=reward, recipient=recipient)
        approved = await self.db.scalar(select(RiskEvent.id).where(RiskEvent.scope == "referral",
            RiskEvent.decision == "approved", RiskEvent.signals_hash["reward_id"].as_string() == reward.id))
        if approved:
            score = 0
        paid = select(func.coalesce(func.sum(ReferralReward.amount_cents), 0)).where(
            ReferralReward.user_id == reward.user_id, ReferralReward.status == "paid")
        total = await self.db.scalar(paid)
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        daily = await self.db.scalar(paid.where(ReferralReward.updated_at >= today))
        limits = total + reward.amount_cents <= await value(self.db, "mall_referral_total_cents")
        limits = limits and daily + reward.amount_cents <= await value(self.db, "mall_referral_daily_cents")
        allowed = permitted and limits and score < await value(self.db, "mall_risk_review_score")
        if allowed and score:
            self.db.add(RiskEvent(user_id=reward.user_id, scope="referral", rule="reward_signals",
                score=score, signals_hash={**signals, "reward_id": reward.id}, decision="allowed"))
        if not allowed:
            self.db.add(RiskEvent(user_id=reward.user_id, scope="referral", rule="reward_eligibility",
                score=score, signals_hash={**signals, "device_hash": relation.device_hash, "ip_hash": relation.ip_hash,
                                         "reward_id": reward.id}, decision="review"))
        return allowed

    async def refund(self, payload):
        rows = list(await self.db.scalars(select(ReferralReward).where(
            ReferralReward.order_id == payload["order_id"]).with_for_update()))
        for row in rows:
            await self._reverse(row)

    async def _reverse(self, row):
        if row.status in {"pending", "review"}:
            await cas(self.db, row, values={"status": "cancelled"})
        elif row.status == "paid":
            try:
                async with self.db.begin_nested():
                    result = await service("wallet", self.db).reverse(row.journal_id,
                        key="reward-reversal:" + row.id, actor_id=row.user_id)
            except MallError as exc:
                if exc.code != "wallet_insufficient":
                    raise
                await cas(self.db, row, values={"status": "receivable"})
                self.db.add(RiskEvent(user_id=row.user_id, scope="referral", rule="reward_receivable",
                    score=DEVICE_RISK_SCORE, signals_hash={"reward_id": row.id}, decision="review"))
                await publish(self.db, row, event_type="mall.referral.receivable", payload={
                    "user_id": row.user_id, "reward_id": row.id, "requires_review": True})
                return
            await cas(self.db, row, values={"status": "reversed", "reversal_id": result["id"]})

    async def reviewed(self, reward_id: str, *, approved: bool):
        row = await self.db.scalar(select(ReferralReward).where(ReferralReward.id == reward_id)
                                   .with_for_update().execution_options(populate_existing=True))
        if row is not None and row.status == "review":
            await cas(self.db, row, values={"status": "pending" if approved else "cancelled"})
