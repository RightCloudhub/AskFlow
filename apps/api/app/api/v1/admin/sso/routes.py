from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.deps import DbSession
from app.schemas.auth import TokenResponse, UserOut
from app.services.auth.oidc import OIDCService

router = APIRouter()


class SSOLoginBody(BaseModel):
    id_token: str


@router.post("/oidc/login")
async def oidc_login(body: SSOLoginBody, db: DbSession) -> dict:
    try:
        token, user = await OIDCService(db).login_with_id_token(body.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {
        "access_token": token.access_token,
        "token_type": token.token_type,
        "user": UserOut.model_validate(user).model_dump(mode="json"),
    }
