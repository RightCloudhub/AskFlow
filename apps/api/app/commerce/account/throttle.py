"""Account/IP failure counters persist even when authentication is rejected."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.commerce.account.crypto import digest
from app.commerce.account.models import LoginAttempt
from app.commerce.core.errors import MallError
from app.commerce.core.repository import insert_once
from app.commerce.core.schemas import utc
from app.core.config import get_settings


async def attempts(db, *, identifier: str, ip: str):
    rows = []
    for scope, value in (("account", identifier.lower()), ("ip", ip)):
        key = digest("login:" + value)
        await insert_once(db, LoginAttempt, values={"scope": scope, "key_hash": key},
                          unique=["scope", "key_hash"])
        row = await db.scalar(select(LoginAttempt).where(
            LoginAttempt.scope == scope, LoginAttempt.key_hash == key).with_for_update())
        if row.locked_until and utc(row.locked_until) > datetime.now(UTC):
            raise MallError("invalid_credentials", status=401)
        rows.append(row)
    return rows


async def failed(db, rows):
    settings, now = get_settings(), datetime.now(UTC)
    for row in rows:
        row.failures += 1
        row.last_failure = now
        if row.failures >= settings.mall_login_max_failures:
            exponent = min(row.failures - settings.mall_login_max_failures, settings.mall_login_max_failures)
            seconds = min(settings.mall_login_max_lock_seconds, settings.mall_login_lock_seconds * (2 ** exponent))
            row.locked_until = now + timedelta(seconds=seconds)
    await db.flush()
    raise MallError("invalid_credentials", status=401, persist=True)


def succeeded(rows):
    for row in rows:
        row.failures, row.locked_until = 0, None
