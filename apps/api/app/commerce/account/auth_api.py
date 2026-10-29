"""Public account endpoints; refresh secrets only leave the service as cookies."""

import hmac
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response

from app.commerce.account import schemas
from app.commerce.account.crypto import digest
from app.commerce.account.hooks import captcha_check
from app.commerce.account.repository import find_identity
from app.commerce.account.service import AccountService
from app.commerce.account.sessions import issue_session, rotate
from app.commerce.account.verification import send_code, verify_code
from app.commerce.core.constants import SECONDS_PER_DAY
from app.commerce.core.deps import MallDb
from app.commerce.core.errors import MallError
from app.commerce.core.idempotency import execute
from app.commerce.core.schemas import utc
from app.commerce.infra.runtime import infra
from app.core.config import get_settings
from app.middleware.rate_limit import client_ip

router = APIRouter()
PUBLIC_TOKEN_FIELDS = ("access_token", "token_type", "expires_in")
COOKIE_PATH = "/api/v1/mall/account"


def token_response(response: Response, bundle: dict):
    settings = get_settings()
    options = {"secure": settings.is_production_like, "samesite": "strict",
               "max_age": settings.mall_refresh_days * SECONDS_PER_DAY}
    response.set_cookie("mall_refresh", bundle["refresh_token"], httponly=True, path=COOKIE_PATH, **options)
    response.set_cookie("mall_csrf", bundle["csrf_token"], httponly=False, path="/", **options)
    return {key: bundle[key] for key in PUBLIC_TOKEN_FIELDS}


@router.post("/verification/send")
async def verification_send(payload: schemas.VerificationSend, db: MallDb):
    return await send_code(db, payload)


@router.post("/verification/verify")
async def verification_verify(payload: schemas.VerifyCode, db: MallDb):
    return await verify_code(db, payload)


@router.get("/verification/demo/{challenge_id}")
async def demo_mailbox(challenge_id: str, request: Request):
    settings = get_settings()
    allowed = settings.env == "test" or (settings.env == "development" and settings.mall_demo_mailbox_enabled)
    if not allowed:
        raise MallError("resource_not_found", status=404)
    value = infra().mailbox.get(challenge_id)
    if value is None or utc(value[0]) <= datetime.now(UTC):
        raise MallError("resource_not_found", status=404)
    return {"code": value[1], "data_source": "mock"}


@router.post("/register", status_code=202)
async def register(payload: schemas.Register, request: Request, db: MallDb):
    await captcha_check(request)
    return await execute(db, scope="register:" + digest(payload.username.lower()),
        key=request.headers.get("idempotency-key", ""), arguments=payload.model_dump(),
        action=lambda: AccountService(db).register(payload, ip=client_ip(request)))


@router.post("/login")
async def login(payload: schemas.Login, request: Request, response: Response, *, db: MallDb):
    await captcha_check(request)
    bundle = await AccountService(db).login(payload, ip=client_ip(request), user_agent=request.headers.get("user-agent", ""))
    return token_response(response, bundle)


@router.post("/refresh")
async def refresh(payload: schemas.Refresh, request: Request, response: Response, *, db: MallDb):
    raw = payload.refresh_token or request.cookies.get("mall_refresh", "")
    csrf = None
    if payload.refresh_token is None:
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf or not hmac.compare_digest(csrf, request.cookies.get("mall_csrf", "")):
            raise MallError("csrf_invalid", status=403)
        if request.headers.get("origin") not in get_settings().cors_origins:
            raise MallError("csrf_invalid", status=403)
    return token_response(response, await rotate(db, raw, csrf=csrf))


@router.post("/password/forgot")
async def forgot(payload: schemas.Forgot, db: MallDb):
    user = await find_identity(db, payload.identifier)
    target = user.email if user else digest(payload.identifier) + "@invalid.local"
    return await send_code(db, schemas.VerificationSend(target=target, channel="email", purpose="password-reset"))


@router.post("/password/reset")
async def reset_password(payload: schemas.ResetPassword, db: MallDb):
    return await AccountService(db).reset_password(payload)


@router.post("/oidc-session")
async def oidc_session(payload: schemas.OidcLogin, response: Response, db: MallDb):
    from app.commerce.account.mfa import verify_factor
    from app.services.auth.oidc import OIDCService

    user = await OIDCService(db).resolve_identity(payload.id_token)
    await verify_factor(db, user.id, payload)
    return token_response(response, await issue_session(db, user, device=payload.device, method="oidc"))
