"""Registration and login (PRD §4.1)."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut


class AuthError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, payload: RegisterRequest, *, role: str = UserRole.USER.value) -> UserOut:
        existing = await self.db.execute(
            select(User).where(
                or_(User.username == payload.username, User.email == payload.email)
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise AuthError("user_exists", "Username or email already registered")

        # Bootstrap: first account becomes admin so ops surfaces are reachable.
        count = await self.db.execute(select(User.id).limit(1))
        if count.scalar_one_or_none() is None:
            role = UserRole.ADMIN.value

        user = User(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return UserOut.model_validate(user)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise AuthError("invalid_credentials", "Invalid username or password")
        if not user.is_active:
            raise AuthError("inactive", "User is inactive")
        token = create_access_token(user.id, role=user.role)
        return TokenResponse(access_token=token)

    async def me(self, user: User) -> UserOut:
        return UserOut.model_validate(user)
