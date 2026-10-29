"""wallet/models persistent entities (amounts are integer minor units)."""

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.migrations.mall_v1.constants import CURRENCY_SIZE, HASH_SIZE, ID_SIZE, NAME_SIZE
from app.migrations.mall_v1.core_models import MallRecord


class WalletAccount(MallRecord):
    __tablename__ = "wallet_accounts"
    __table_args__ = (CheckConstraint("allow_negative OR balance_cents >= 0", name="wallet_accounts_check_0"), CheckConstraint("normal_side IN ('debit','credit')", name="wallet_accounts_check_1"),)
    user_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    currency: Mapped[str] = mapped_column(String(CURRENCY_SIZE), nullable=False)
    normal_side: Mapped[str] = mapped_column(String(NAME_SIZE), default="credit", nullable=False)
    balance_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    allow_negative: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class WalletChainHead(MallRecord):
    __tablename__ = "wallet_chain_heads"
    currency: Mapped[str] = mapped_column(String(CURRENCY_SIZE), nullable=False, unique=True)
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_hash: Mapped[str] = mapped_column(String(HASH_SIZE), default="", nullable=False)


class JournalEntry(MallRecord):
    __tablename__ = "wallet_journal_entries"
    __table_args__ = (CheckConstraint("total_cents > 0", name="wallet_journal_entries_check_0"), UniqueConstraint("currency", "seq"),)
    business_key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    currency: Mapped[str] = mapped_column(String(CURRENCY_SIZE), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    total_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(HASH_SIZE), default="", nullable=False)
    row_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False)
    reversal_of: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("wallet_journal_entries.id", ondelete="RESTRICT"), nullable=True, unique=True, index=True)


class Posting(MallRecord):
    __tablename__ = "wallet_postings"
    __table_args__ = (CheckConstraint("side IN ('debit','credit')", name="wallet_postings_check_0"), CheckConstraint("amount_cents > 0", name="wallet_postings_check_1"),)
    journal_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("wallet_journal_entries.id", ondelete="RESTRICT"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("wallet_accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
