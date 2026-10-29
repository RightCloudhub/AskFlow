"""Dialect-specific append-only protections for financial evidence."""

from sqlalchemy import text

TABLES = ("wallet_journal_entries", "wallet_postings")
PG_FUNCTION = """
CREATE OR REPLACE FUNCTION mall_reject_financial_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'financial entries are append-only'; END;
$$ LANGUAGE plpgsql
"""


def install(connection):
    if connection.dialect.name == "postgresql":
        connection.execute(text(PG_FUNCTION))
    for table in TABLES:
        for operation in ("UPDATE", "DELETE"):
            install_trigger(connection, table, operation)


def install_trigger(connection, table, operation):
    name = "mall_" + table + "_" + operation.lower()
    if connection.dialect.name == "sqlite":
        sql = f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'financial entries are append-only'); END"
    else:
        present = connection.scalar(text("SELECT 1 FROM pg_trigger WHERE tgname=:name "
            "AND tgrelid=CAST(:table AS regclass)"), {"name": name, "table": table})
        if present:
            return
        sql = f"CREATE TRIGGER {name} BEFORE {operation} ON {table} FOR EACH ROW EXECUTE FUNCTION mall_reject_financial_mutation()"
    connection.execute(text(sql))


def remove(connection):
    for table in TABLES:
        for operation in ("UPDATE", "DELETE"):
            suffix = " ON " + table if connection.dialect.name == "postgresql" else ""
            connection.execute(text(f"DROP TRIGGER IF EXISTS mall_{table}_{operation.lower()}{suffix}"))
    if connection.dialect.name == "postgresql":
        connection.execute(text("DROP FUNCTION IF EXISTS mall_reject_financial_mutation()"))
