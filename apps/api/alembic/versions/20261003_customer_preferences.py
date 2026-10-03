"""Add customer-confirmed preference memory.

Revision ID: 20261003_customer_preferences
Revises: 20261003_service_tasks
"""

from alembic import op
import sqlalchemy as sa

revision = "20261003_customer_preferences"
down_revision = "20261003_service_tasks"
branch_labels = None
depends_on = None
ID_LENGTH = 36
SCOPE_LENGTH = 128
PREFERENCE_LENGTH = 32


def upgrade() -> None:
    op.create_table(
        "customer_preferences",
        sa.Column("id", sa.String(ID_LENGTH), primary_key=True),
        sa.Column("organization_id", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("customer_id", sa.String(SCOPE_LENGTH), nullable=False),
        sa.Column("key", sa.String(PREFERENCE_LENGTH), nullable=False),
        sa.Column("value", sa.String(PREFERENCE_LENGTH), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "customer_id", "key",
                            name="uq_customer_preference_scope_key"),
    )


def downgrade() -> None:
    op.drop_table("customer_preferences")
