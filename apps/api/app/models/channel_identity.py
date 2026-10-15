"""Account linking: channel user ids map to one internal principal with assurance (arch §4.2)."""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

ID_LENGTH = 36
NAME_LENGTH = 128
EXTERNAL_ID_LENGTH = 255
ASSURANCE_ANONYMOUS = 0
ASSURANCE_CHANNEL_VERIFIED = 1
ASSURANCE_AUTHENTICATED = 2


class ChannelIdentity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "channel_identities"
    __table_args__ = (
        UniqueConstraint("channel", "channel_user_id", name="uq_channel_identity_user"),
    )

    channel: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False, index=True)
    channel_user_id: Mapped[str] = mapped_column(String(EXTERNAL_ID_LENGTH), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(ID_LENGTH), ForeignKey("users.id"), nullable=False, index=True
    )
    assurance_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
