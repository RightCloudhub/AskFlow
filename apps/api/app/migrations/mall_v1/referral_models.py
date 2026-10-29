"""referral/models persistent entities (amounts are integer minor units)."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.migrations.mall_v1.constants import HASH_SIZE, ID_SIZE, NAME_SIZE
from app.migrations.mall_v1.core_models import MallRecord


class ReferralCode(MallRecord):
    __tablename__ = "referral_codes"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)


class ReferralRelation(MallRecord):
    __tablename__ = "referral_relations"
    __table_args__ = (CheckConstraint("inviter_id != invitee_id", name="referral_relations_check_0"),)
    inviter_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    invitee_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    code_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("referral_codes.id", ondelete="RESTRICT"), nullable=False, index=True)
    device_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ReferralReward(MallRecord):
    __tablename__ = "referral_rewards"
    __table_args__ = (UniqueConstraint("relation_id", "order_id", "rule_version"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    relation_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("referral_relations.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    rule_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending", nullable=False, index=True)
    eligible_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    journal_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("wallet_journal_entries.id", ondelete="RESTRICT"), nullable=True, index=True)
    reversal_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("wallet_journal_entries.id", ondelete="RESTRICT"), nullable=True, index=True)


class RiskEvent(MallRecord):
    __tablename__ = "risk_events"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    rule: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signals_hash: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    decision: Mapped[str] = mapped_column(String(NAME_SIZE), default="review", nullable=False, index=True)
    review_actor: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    review_note: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
