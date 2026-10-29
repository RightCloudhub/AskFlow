"""Offline-default extension hooks; enabled checks require explicit adapters."""

from http import HTTPStatus

from app.commerce.core.errors import MallError
from app.core.config import get_settings
from app.plugins.runtime import require_app_context


async def password_policy(password: str):
    settings = get_settings()
    if not settings.mall_password_min_length <= len(password) <= settings.mall_password_max_length:
        raise MallError("password_policy_failed", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    if not all((any(c.isupper() for c in password), any(c.islower() for c in password),
                any(c.isdigit() for c in password))):
        raise MallError("password_policy_failed", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    if settings.mall_password_breach_check:
        checker = require_app_context().services.get("mall_password_breach_checker")
        if checker is None or await checker(password):
            raise MallError("password_breach_check_failed", status=HTTPStatus.UNPROCESSABLE_ENTITY)


async def captcha_check(request):
    if not get_settings().mall_captcha_enabled:
        return
    checker = require_app_context().services.get("mall_captcha_checker")
    if checker is None or not await checker(request):
        raise MallError("captcha_required", status=HTTPStatus.FORBIDDEN)
