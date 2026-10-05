"""Add scoped facts, timeline/experience memory, and business-object leases."""

import sqlalchemy as sa

from alembic import op

revision = "20261004_agent_memories_locks"
down_revision = "20261003_service_dispatches"
branch_labels = None
depends_on = None
ID_LENGTH = 36
SCOPE_LENGTH = 128
KIND_LENGTH = 32
KEY_LENGTH = 255


def upgrade() -> None:
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.String(ID_LENGTH), primary_key=True),
        sa.Column("organization_id", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("customer_id", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("kind", sa.String(KIND_LENGTH), nullable=False),
        sa.Column("key", sa.String(KEY_LENGTH), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("verification", sa.String(KIND_LENGTH), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_id", "customer_id", "kind", "key", name="uq_agent_memory_scope_kind_key"
        ),
    )
    op.create_table(
        "service_object_locks",
        sa.Column("id", sa.String(ID_LENGTH), primary_key=True),
        sa.Column("organization_id", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("customer_id", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("object_key", sa.String(KEY_LENGTH), nullable=False),
        sa.Column("task_id", sa.String(ID_LENGTH), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_id", "customer_id", "object_key", name="uq_service_object_lock_scope_key"
        ),
    )


def downgrade() -> None:
    op.drop_table("service_object_locks")
    op.drop_table("agent_memories")
