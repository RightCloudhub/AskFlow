"""Bootstrap missing core tables and add frozen commerce schema.

Revision ID: 20261029_mall_v1
Revises: 20261016_document_metadata

The snapshot is independent of live ORM models. Existing core tables are left
untouched. Downgrade removes only commerce tables, never legacy customer data.
"""

from alembic import op

from app.migrations.mall_v1 import MALL_TABLES, metadata
from app.migrations.mall_v1.integrity import install, remove

revision = "20261029_mall_v1"
down_revision = "20261016_document_metadata"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    schema = metadata()
    schema.create_all(connection, checkfirst=True)
    install(connection)


def downgrade():
    connection = op.get_bind()
    remove(connection)
    schema = metadata()
    for table in reversed(schema.sorted_tables):
        if table.name in MALL_TABLES:
            table.drop(connection, checkfirst=True)
