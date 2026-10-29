"""Bootstrap retained customer-service tables before migrations that reference users.

Existing revision IDs remain valid. Downgrade retains the legacy tables because
they may predate Alembic; it must never erase customer-service data.
"""

from alembic import op

from app.migrations.mall_v1.bootstrap import install

revision = "20261002_core_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    install(op.get_bind())


def downgrade():
    """Preserve legacy data, including tables adopted from create_all deployments."""
