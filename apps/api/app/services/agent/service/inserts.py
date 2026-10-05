"""Conflict-safe inserts supported by the application's SQLite and PostgreSQL databases."""

from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


async def insert_once(db, model, *, values: dict, key: str) -> None:
    dialect = db.bind.dialect.name
    insert = {"sqlite": sqlite_insert, "postgresql": postgres_insert}[dialect]
    await db.execute(insert(model).values(**values).on_conflict_do_nothing(index_elements=[key]))
