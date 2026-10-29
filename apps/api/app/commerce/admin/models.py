"""admin/models persistent entities (amounts are integer minor units)."""

from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import ID_SIZE, NAME_SIZE
from app.commerce.core.models import MallRecord


class AdminRole(MallRecord):
    __tablename__ = "admin_roles"
    code: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AdminPermission(MallRecord):
    __tablename__ = "admin_permissions"
    code: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)


class RolePermission(MallRecord):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_code"),)
    role_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("admin_roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    permission_code: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)


class UserRoleGrant(MallRecord):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("admin_roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)


class MallSetting(MallRecord):
    __tablename__ = "mall_settings"
    key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    modified_by: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)


class SettingRevision(MallRecord):
    __tablename__ = "mall_setting_revisions"
    __table_args__ = (UniqueConstraint("key", "version"),)
    key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    modified_by: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

