"""Add persistent service dispatches.

Revision ID: 20261003_service_dispatches
Revises: 20261003_customer_preferences
"""

from alembic import op
import sqlalchemy as sa

revision = "20261003_service_dispatches"
down_revision = "20261003_customer_preferences"
branch_labels = None
depends_on = None
ID_LENGTH = 36
ERROR_CODE_LENGTH = 64


def upgrade():
    op.create_table(
        "service_dispatches",
        sa.Column("task_id", sa.String(ID_LENGTH), primary_key=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.String(ID_LENGTH), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("notified_version", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(ERROR_CODE_LENGTH), nullable=True),
    )
    op.create_index("ix_service_dispatches_due_at", "service_dispatches", ["due_at"])


def downgrade():
    op.drop_table("service_dispatches")
