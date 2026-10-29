"""account/models persistent entities (amounts are integer minor units)."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.migrations.mall_v1.constants import HASH_SIZE, ID_SIZE, NAME_SIZE
from app.migrations.mall_v1.core_models import MallRecord


class UserProfile(MallRecord):
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    phone_cipher: Mapped[str] = mapped_column(Text, default="", nullable=False)
    phone_hash: Mapped[str | None] = mapped_column(String(HASH_SIZE), nullable=True, unique=True)
    avatar: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    region: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    locale: Mapped[str] = mapped_column(String(NAME_SIZE), default="zh-CN", nullable=False)


class UserSecurity(MallRecord):
    __tablename__ = "user_security"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_cipher: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pending_totp_cipher: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_totp_step: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)
    auth_epoch: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class UserSession(MallRecord):
    __tablename__ = "user_sessions"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String(ID_SIZE), nullable=False, index=True)
    refresh_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False, unique=True)
    parent_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("user_sessions.id", ondelete="RESTRICT"), nullable=True, index=True)
    device: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    auth_method: Mapped[str] = mapped_column(String(NAME_SIZE), default="password", nullable=False)
    csrf_hash: Mapped[str] = mapped_column(String(HASH_SIZE), default="", nullable=False)


class AccessRevocation(MallRecord):
    __tablename__ = "access_revocations"
    jti: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class VerificationCode(MallRecord):
    __tablename__ = "verification_codes"
    user_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    target_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False, index=True)
    target_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    purpose: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    proof_hash: Mapped[str] = mapped_column(String(HASH_SIZE), default="", nullable=False)
    delivery_cipher: Mapped[str] = mapped_column(Text, default="", nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending", nullable=False)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_next_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class RecoveryCode(MallRecord):
    __tablename__ = "recovery_codes"
    __table_args__ = (UniqueConstraint("user_id", "code_hash"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class LoginAttempt(MallRecord):
    __tablename__ = "login_attempts"
    __table_args__ = (UniqueConstraint("scope", "key_hash"),)
    scope: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False)
    failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_failure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class Address(MallRecord):
    __tablename__ = "addresses"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    name_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    phone_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    address_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class SecurityReset(MallRecord):
    __tablename__ = "user_security_resets"
    __table_args__ = (CheckConstraint("approved_by IS NULL OR approved_by != requested_by", name="security_reset_dual_control"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reason: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending", nullable=False)

