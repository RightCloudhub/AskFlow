"""Retrieval metadata on documents: language, product, ACL groups, validity (arch §4.7)."""

import sqlalchemy as sa

from alembic import op

revision = "20261016_document_metadata"
down_revision = "20261015_governance_tables"
branch_labels = None
depends_on = None

COLUMNS = {
    "language": sa.String(16),
    "product": sa.String(64),
    "acl_groups": sa.JSON(),
    "valid_from": sa.DateTime(timezone=True),
    "valid_to": sa.DateTime(timezone=True),
}


def _existing_columns(bind) -> set[str]:
    if "documents" not in sa.inspect(bind).get_table_names():
        return set()
    return {column["name"] for column in sa.inspect(bind).get_columns("documents")}


def upgrade() -> None:
    bind = op.get_bind()
    existing = _existing_columns(bind)
    if not existing:
        return
    with op.batch_alter_table("documents") as batch:
        for name, column_type in COLUMNS.items():
            if name not in existing:
                batch.add_column(sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    existing = _existing_columns(bind)
    if not existing:
        return
    with op.batch_alter_table("documents") as batch:
        for name in COLUMNS:
            if name in existing:
                batch.drop_column(name)
