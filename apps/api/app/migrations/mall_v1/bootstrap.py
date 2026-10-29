"""Frozen pre-service schema for empty installs; later revisions own their tables."""

import sqlalchemy as sa

from app.migrations.mall_v1 import MALL_TABLES, metadata

MIGRATED_TABLES = frozenset({
    "service_tasks", "customer_preferences", "service_dispatches", "agent_memories",
    "service_object_locks", "operation_ledger", "outbox", "channel_inbox",
    "router_decisions", "channel_identities", "otp_challenges", "confirmation_nonces",
})
ID_LENGTH = 36
USERNAME_LENGTH = 64
EMAIL_LENGTH = 255
ROLE_LENGTH = 32


def users_table():
    return sa.Table(
        "users", sa.MetaData(),
        sa.Column("id", sa.String(ID_LENGTH), primary_key=True),
        sa.Column("username", sa.String(USERNAME_LENGTH), nullable=False,
                  unique=True, index=True),
        sa.Column("email", sa.String(EMAIL_LENGTH), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(EMAIL_LENGTH), nullable=False),
        sa.Column("role", sa.String(ROLE_LENGTH), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )


def install(connection):
    users_table().create(connection, checkfirst=True)
    for table in metadata().sorted_tables:
        if table.name not in MALL_TABLES | MIGRATED_TABLES | {"users"}:
            table.create(connection, checkfirst=True)
