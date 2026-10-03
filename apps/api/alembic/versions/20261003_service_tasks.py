"""Add versioned service task checkpoints.

Revision ID: 20261003_service_tasks
Revises: None (first checked-in migration; existing tables are bootstrapped separately).
"""

import sqlalchemy as sa

from alembic import op

revision = "20261003_service_tasks"
down_revision = None
branch_labels = None
depends_on = None
ID_LENGTH = 36
SCOPE_LENGTH = 128


def upgrade() -> None:
    op.create_table(
        "service_tasks",
        sa.Column("id", sa.String(ID_LENGTH), primary_key=True),
        sa.Column("organization_id", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("customer_id", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("checkpoint", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_service_tasks_organization_id", "service_tasks", ["organization_id"])
    op.create_index("ix_service_tasks_customer_id", "service_tasks", ["customer_id"])


def downgrade() -> None:
    op.drop_table("service_tasks")
