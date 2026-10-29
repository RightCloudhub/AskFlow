"""Parameterized insert/CAS primitives and mandatory ownership filtering."""

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.errors import MallError


async def insert_once(db, model, *, values: dict, unique: list[str] | None = None) -> bool:
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    statement = insert(model).values(**values).on_conflict_do_nothing(index_elements=unique or None)
    result = await db.execute(statement)
    return result.rowcount == 1


async def owned(db, model, *, owner_id: str, resource_id: str, lock: bool = False):
    statement = select(model).where(model.id == resource_id, model.user_id == owner_id)
    if lock:
        statement = statement.with_for_update()
    row = await db.scalar(statement.execution_options(populate_existing=True))
    if row is None:
        raise MallError("resource_not_found", status=status.HTTP_404_NOT_FOUND)
    return row


async def owned_page(db, model, *, owner_id: str, cursor: str = "", filters: tuple = ()):
    statement = select(model).where(model.user_id == owner_id, model.id > cursor, *filters)
    rows = list(await db.scalars(statement.order_by(model.id).limit(PAGE_SIZE + 1)))
    return rows[:PAGE_SIZE], rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None


async def cas(db, row, *, values: dict, conditions: tuple = ()):
    model = type(row)
    result = await db.execute(
        update(model).where(model.id == row.id, model.version == row.version, *conditions)
        .values(**values, version=model.version + 1).execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise MallError("version_conflict")
    await db.refresh(row)
    return row
