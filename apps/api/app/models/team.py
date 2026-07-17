"""Skill teams for agent queue scoping (PRD Wave B / §12.2)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Team(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    # comma-separated intents this team handles, e.g. "fault_report,complaint"
    intent_scope: Mapped[str] = mapped_column(String(512), default="", nullable=False)


class TeamMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_member"),)

    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    role_in_team: Mapped[str] = mapped_column(String(32), default="member", nullable=False)
