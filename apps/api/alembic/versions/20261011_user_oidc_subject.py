"""Bind SSO accounts to the IdP's stable ``sub`` instead of email (audit D-02)."""

import sqlalchemy as sa

from alembic import op

revision = "20261011_user_oidc_subject"
down_revision = "20261004_agent_memories_locks"
branch_labels = None
depends_on = None
SUBJECT_LENGTH = 255
INDEX_NAME = "ix_users_oidc_subject"


def _users_table_exists() -> bool:
    # Core tables are created by ``init_db`` (create_all); only pre-existing ones need the column.
    return "users" in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _users_table_exists():
        return
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("oidc_subject", sa.String(SUBJECT_LENGTH), nullable=True))
        batch.create_index(INDEX_NAME, ["oidc_subject"], unique=True)


def downgrade() -> None:
    if not _users_table_exists():
        return
    with op.batch_alter_table("users") as batch:
        batch.drop_index(INDEX_NAME)
        batch.drop_column("oidc_subject")
