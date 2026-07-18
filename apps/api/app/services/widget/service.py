"""Guest widget sessions (PRD E7a) — same Agent pipeline via ChatService."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.chat import ConversationCreate
from app.services.audit.logger.service import AuditService
from app.services.chat.session.service import ChatService
from app.utils.ids import new_id

# Short-lived guest JWT (cost / abuse surface)
GUEST_TOKEN_MINUTES = 120
USERNAME_PREFIX = "guest_"
EMAIL_DOMAIN = "guest.askflow.local"
# sha256 hex prefix — collision-resistant, email/username-safe charset
VISITOR_ID_HEX_LEN = 32
TITLE_MAX = 40


def sanitize_visitor_key(raw: str | None) -> str:
    """Map raw visitor keys to a stable, collision-free identity id.

    Char-rewrite (e.g. ``@`` → ``_``) is unsafe: ``va@evil`` and ``va_evil``
    must remain distinct users. Hash the exact raw string (UTF-8).
    ``None`` / blank → fresh random id (anonymous one-shot guest).
    """
    if raw is None or not str(raw).strip():
        base = new_id()
    else:
        base = str(raw)
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return digest[:VISITOR_ID_HEX_LEN]


@dataclass
class WidgetSession:
    access_token: str
    user_id: str
    conversation_id: str
    visitor_key: str


class WidgetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def open_session(
        self,
        *,
        visitor_key: str | None = None,
        title: str = "官网咨询",
        origin: str | None = None,
    ) -> WidgetSession:
        key = sanitize_visitor_key(visitor_key)
        user = await self._ensure_guest(key)
        conv = await ChatService(self.db).create_conversation(
            user.id,
            ConversationCreate(title=(title or "官网咨询")[:TITLE_MAX]),
        )
        token = create_access_token(
            user.id,
            role=UserRole.USER.value,
            extra={"guest": True, "visitor_key": key, "channel": "widget"},
            expires_minutes=GUEST_TOKEN_MINUTES,
        )
        await AuditService(self.db).log(
            action="widget.session_open",
            resource_type="conversation",
            resource_id=conv.id,
            actor_id=user.id,
            detail={"visitor_key": key, "origin": origin},
        )
        return WidgetSession(
            access_token=token,
            user_id=user.id,
            conversation_id=conv.id,
            visitor_key=key,
        )

    async def _ensure_guest(self, visitor_key: str) -> User:
        from sqlalchemy.exc import IntegrityError

        username = f"{USERNAME_PREFIX}{visitor_key}"[:64]
        email = f"{visitor_key}@{EMAIL_DOMAIN}"[:255]
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is not None:
            return user
        try:
            async with self.db.begin_nested():
                user = User(
                    username=username,
                    email=email,
                    hashed_password=hash_password(new_id() + "guest"),
                    role=UserRole.USER.value,
                )
                self.db.add(user)
                await self.db.flush()
            await self.db.refresh(user)
            return user
        except IntegrityError:
            result = await self.db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is None:
                raise
            return user
