"""Governance tables: operation ledger, outbox, inbox, router decisions, identity (arch §10.6)."""

import sqlalchemy as sa

from alembic import op

revision = "20261015_governance_tables"
down_revision = "20261011_user_oidc_subject"
branch_labels = None
depends_on = None

ID_LENGTH = 36
NAME_LENGTH = 128
HASH_LENGTH = 64
STATUS_LENGTH = 32
REF_LENGTH = 255
METHOD_LENGTH = 32
VERSION_LENGTH = 32
EXTERNAL_ID_LENGTH = 255
SESSION_KEY_LENGTH = 255
PURPOSE_LENGTH = 64
STEP_LENGTH = 128

ID = sa.String(ID_LENGTH)
NAME = sa.String(NAME_LENGTH)
HASH = sa.String(HASH_LENGTH)
TABLES = (
    "operation_ledger",
    "outbox",
    "channel_inbox",
    "router_decisions",
    "channel_identities",
    "otp_challenges",
    "confirmation_nonces",
)


def _missing(bind, table: str) -> bool:
    # Core tables may already exist from ``init_db`` (create_all); only create what is absent.
    return table not in sa.inspect(bind).get_table_names()


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _create_operation_ledger() -> None:
    op.create_table(
        "operation_ledger",
        sa.Column("seq", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("op_id", ID, nullable=False, unique=True),
        sa.Column("organization_id", NAME, nullable=False),
        sa.Column("customer_id", NAME, nullable=False),
        sa.Column("task_id", ID, nullable=True),
        sa.Column("turn_id", ID, nullable=True),
        sa.Column("step", NAME, nullable=True),
        sa.Column("capability", NAME, nullable=False),
        sa.Column("capability_version", NAME, nullable=False),
        sa.Column("args_hash", HASH, nullable=False),
        sa.Column("idempotency_key", NAME, nullable=False),
        sa.Column("policy_decision", sa.JSON(), nullable=False),
        sa.Column("policy_version", NAME, nullable=False),
        sa.Column("actor", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("status", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("external_ref", sa.String(REF_LENGTH), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost", sa.JSON(), nullable=True),
        sa.Column("prev_hash", HASH, nullable=True),
        sa.Column("row_hash", HASH, nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_operation_ledger_op_id", "operation_ledger", ["op_id"])
    op.create_index("ix_operation_ledger_idempotency_key", "operation_ledger", ["idempotency_key"])


def _create_outbox() -> None:
    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("aggregate", NAME, nullable=False),
        sa.Column("aggregate_id", ID, nullable=False),
        sa.Column("event_type", NAME, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(REF_LENGTH), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_outbox_aggregate_id", "outbox", ["aggregate_id"])
    op.create_index("ix_outbox_event_type", "outbox", ["event_type"])
    op.create_index("ix_outbox_published_at", "outbox", ["published_at"])


def _create_channel_inbox() -> None:
    op.create_table(
        "channel_inbox",
        sa.Column("id", ID, primary_key=True),
        sa.Column("channel", NAME, nullable=False),
        sa.Column("channel_message_id", sa.String(EXTERNAL_ID_LENGTH), nullable=False),
        sa.Column("session_key", sa.String(SESSION_KEY_LENGTH), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.String(EXTERNAL_ID_LENGTH), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(REF_LENGTH), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("channel", "channel_message_id", name="uq_channel_inbox_message"),
    )
    op.create_index("ix_channel_inbox_channel", "channel_inbox", ["channel"])
    op.create_index("ix_channel_inbox_session_key", "channel_inbox", ["session_key"])
    op.create_index("ix_channel_inbox_published_at", "channel_inbox", ["published_at"])


def _create_router_decisions() -> None:
    op.create_table(
        "router_decisions",
        sa.Column("id", ID, primary_key=True),
        sa.Column("turn_id", ID, nullable=False),
        sa.Column("conversation_id", ID, nullable=False),
        sa.Column("route", sa.String(METHOD_LENGTH), nullable=False),
        sa.Column("goal_key", NAME, nullable=True),
        sa.Column("goal_version", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("method", sa.String(METHOD_LENGTH), nullable=False),
        sa.Column("slots", sa.JSON(), nullable=False),
        sa.Column("missing_slots", sa.JSON(), nullable=False),
        sa.Column("identity_requirement", sa.JSON(), nullable=True),
        sa.Column("active_task_relation", sa.String(METHOD_LENGTH), nullable=True),
        sa.Column("router_version", sa.String(VERSION_LENGTH), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )
    op.create_index("ix_router_decisions_turn_id", "router_decisions", ["turn_id"])
    op.create_index("ix_router_decisions_conversation_id", "router_decisions", ["conversation_id"])
    op.create_index("ix_router_decisions_route", "router_decisions", ["route"])


def _create_channel_identities() -> None:
    op.create_table(
        "channel_identities",
        sa.Column("id", ID, primary_key=True),
        sa.Column("channel", NAME, nullable=False),
        sa.Column("channel_user_id", sa.String(EXTERNAL_ID_LENGTH), nullable=False),
        sa.Column("user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assurance_level", sa.Integer(), nullable=False, server_default="1"),
        *_timestamps(),
        sa.UniqueConstraint("channel", "channel_user_id", name="uq_channel_identity_user"),
    )
    op.create_index("ix_channel_identities_channel", "channel_identities", ["channel"])
    op.create_index("ix_channel_identities_user_id", "channel_identities", ["user_id"])


def _create_otp_challenges() -> None:
    op.create_table(
        "otp_challenges",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, nullable=False),
        sa.Column("conversation_id", ID, nullable=True),
        sa.Column("channel", NAME, nullable=False),
        sa.Column("purpose", sa.String(PURPOSE_LENGTH), nullable=False, server_default="step_up"),
        sa.Column("code_hash", HASH, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_otp_challenges_user_id", "otp_challenges", ["user_id"])
    op.create_index("ix_otp_challenges_conversation_id", "otp_challenges", ["conversation_id"])


def _create_confirmation_nonces() -> None:
    op.create_table(
        "confirmation_nonces",
        sa.Column("id", ID, primary_key=True),
        sa.Column("nonce", HASH, nullable=False, unique=True),
        sa.Column("task_id", ID, nullable=True),
        sa.Column("turn_id", ID, nullable=True),
        sa.Column("step", sa.String(STEP_LENGTH), nullable=False, server_default=""),
        sa.Column("args_hash", HASH, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_confirmation_nonces_nonce", "confirmation_nonces", ["nonce"])
    op.create_index("ix_confirmation_nonces_task_id", "confirmation_nonces", ["task_id"])


CREATORS = {
    "operation_ledger": _create_operation_ledger,
    "outbox": _create_outbox,
    "channel_inbox": _create_channel_inbox,
    "router_decisions": _create_router_decisions,
    "channel_identities": _create_channel_identities,
    "otp_challenges": _create_otp_challenges,
    "confirmation_nonces": _create_confirmation_nonces,
}


def upgrade() -> None:
    bind = op.get_bind()
    for table, create in CREATORS.items():
        if _missing(bind, table):
            create()


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    for table in reversed(TABLES):
        if table in existing:
            op.drop_table(table)
