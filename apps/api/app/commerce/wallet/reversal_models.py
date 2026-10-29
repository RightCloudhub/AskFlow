"""Two-person financial reversals retain the original append-only journal."""

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import ID_SIZE, NAME_SIZE
from app.commerce.core.models import MallRecord


class ReversalRequest(MallRecord):
    __tablename__ = "wallet_reversal_requests"
    __table_args__ = (
        CheckConstraint("approved_by IS NULL OR approved_by != requested_by",
                        name="wallet_reversal_dual_control"),
    )
    original_id: Mapped[str] = mapped_column(
        ForeignKey("wallet_journal_entries.id", ondelete="RESTRICT"), index=True)
    requested_by: Mapped[str] = mapped_column(
        String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"))
    approved_by: Mapped[str | None] = mapped_column(
        String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"))
    journal_id: Mapped[str | None] = mapped_column(
        ForeignKey("wallet_journal_entries.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(String(NAME_SIZE))
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending", index=True)
