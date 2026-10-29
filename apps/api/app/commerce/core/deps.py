"""Mall sessions start SQLite writes before authentication reads."""

from dataclasses import dataclass
from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select, text

from app.commerce.core.errors import MallError
from app.core import database
from app.core.security import decode_access_token
from app.models.user import User

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


async def mall_db(request: Request):
    async with database.SessionLocal() as db:
        if db.bind.dialect.name == "sqlite" and request.method in WRITE_METHODS:
            await db.execute(text("BEGIN IMMEDIATE"))
        try:
            yield db
            await db.commit()
        except MallError as exc:
            await finish_error(db, exc)
            raise
        except Exception:
            await db.rollback()
            raise


async def finish_error(db, error):
    if error.persist:
        await db.commit()
        return
    await db.rollback()


MallDb = Annotated[database.AsyncSession, Depends(mall_db)]


@dataclass
class Context:
    db: database.AsyncSession
    user: User
    request: Request
    claims: dict

    @property
    def key(self) -> str:
        return self.request.headers.get("idempotency-key", "")


async def context(request: Request, db: MallDb) -> Context:
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise MallError("authentication_required", status=HTTPStatus.UNAUTHORIZED)
    try:
        claims = decode_access_token(header.removeprefix("Bearer "))
    except ValueError as exc:
        raise MallError("invalid_credentials", status=HTTPStatus.UNAUTHORIZED) from exc
    if _invalid_scope(claims):
        raise MallError("invalid_credentials", status=HTTPStatus.UNAUTHORIZED)
    statement = select(User).where(User.id == claims.get("sub"), User.is_active)
    if request.method in WRITE_METHODS:
        statement = statement.with_for_update(key_share=True)
    user = await db.scalar(statement.execution_options(populate_existing=True))
    if user is None:
        raise MallError("invalid_credentials", status=HTTPStatus.UNAUTHORIZED)
    from app.commerce.account.sessions import validate_access

    await validate_access(db, claims)
    request.state.mall_user_id = user.id
    return Context(db, user, request, claims)


MallContext = Annotated[Context, Depends(context)]


def _invalid_scope(claims: dict) -> bool:
    return bool(claims.get("guest") or claims.get("channel") in {"guest", "widget"}
                or claims.get("type", "access") != "access")
