"""support/models persistent entities (amounts are integer minor units)."""

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.migrations.mall_v1.constants import ID_SIZE
from app.migrations.mall_v1.core_models import MallRecord


class SupportLink(MallRecord):
    __tablename__ = "support_links"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True, index=True)
    refund_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("refunds.id", ondelete="RESTRICT"), nullable=True, index=True)
    wallet_journal_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("wallet_journal_entries.id", ondelete="RESTRICT"), nullable=True, index=True)
    conversation_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True)
    ticket_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("tickets.id", ondelete="RESTRICT"), nullable=True, index=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
