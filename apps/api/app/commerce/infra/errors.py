"""Known adapter failures; optional SDK exceptions are loaded only when available."""

from importlib.util import find_spec

import httpx
from sqlalchemy.exc import SQLAlchemyError

from app.commerce.core.errors import MallError


def dependency_errors():
    errors = (OSError, TimeoutError, ConnectionError, ValueError, RuntimeError,
              ImportError, httpx.HTTPError, SQLAlchemyError, MallError)
    if find_spec("redis") is not None:
        from redis.exceptions import RedisError

        errors += (RedisError,)
    if find_spec("botocore") is not None:
        from botocore.exceptions import BotoCoreError, ClientError

        errors += (BotoCoreError, ClientError)
    return errors
