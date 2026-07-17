"""Security hardening regressions (C1, H1–H3, path escape, guest scope)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.core.security import create_access_token, decode_access_token, hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.auth.service import AuthService
from app.services.knowledge.storage.local import LocalObjectStorage, safe_filename
from app.services.widget.service import WidgetService


def test_safe_filename_blocks_traversal():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert ".." not in safe_filename("../x")
    assert "/" not in safe_filename("a/b/c.txt")


def test_local_storage_rejects_path_escape(tmp_path: Path):
    store = LocalObjectStorage(root=tmp_path)
    store.put("documents/id1/ok.txt", b"hi")
    with pytest.raises(ValueError, match="path_escape"):
        store.put("../escape.txt", b"nope")
    with pytest.raises(ValueError, match="path_escape"):
        store.put("documents/../../escape.txt", b"nope")


def test_production_rejects_oidc_mock_at_startup():
    s = Settings(
        ASKFLOW_ENV="production",
        SECRET_KEY="strong-secret-key-32chars-min!!",
        OIDC_MOCK=True,
    )
    with pytest.raises(RuntimeError, match="OIDC_MOCK"):
        s.assert_startup_safe()


def test_local_register_denied_in_production_by_default():
    s = Settings(
        ASKFLOW_ENV="production",
        SECRET_KEY="strong-secret-key-32chars-min!!",
    )
    assert s.local_register_allowed() is False
    assert s.bootstrap_admin_allowed() is False
    s2 = Settings(
        ASKFLOW_ENV="production",
        SECRET_KEY="strong-secret-key-32chars-min!!",
        ALLOW_LOCAL_REGISTER=True,
        ALLOW_BOOTSTRAP_ADMIN=True,
    )
    assert s2.local_register_allowed() is True
    assert s2.bootstrap_admin_allowed() is True


def test_guest_token_has_guest_claim():
    token = create_access_token(
        "uid-1",
        role=UserRole.USER.value,
        extra={"guest": True, "channel": "widget"},
        expires_minutes=30,
    )
    payload = decode_access_token(token)
    assert payload.get("guest") is True
    assert payload.get("channel") == "widget"


@pytest.mark.asyncio
async def test_bootstrap_admin_only_when_allowed():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        # Simulate production-like bootstrap policy via monkeypatch on get_settings inside register
        from app.core import config as cfg

        prod = Settings(
            ASKFLOW_ENV="production",
            SECRET_KEY="strong-secret-key-32chars-min!!",
            ALLOW_LOCAL_REGISTER=True,
            ALLOW_BOOTSTRAP_ADMIN=False,
        )
        orig = cfg.get_settings
        cfg.get_settings = lambda: prod  # type: ignore[assignment]
        try:
            user = await AuthService(db).register(
                RegisterRequest(username="firstu", email="f@e.com", password="password123")
            )
            assert user.role == UserRole.USER.value
        finally:
            cfg.get_settings = orig  # type: ignore[assignment]
    await engine.dispose()


@pytest.mark.asyncio
async def test_widget_guest_token_cannot_use_chat_rest(client):
    """Guest JWT must be rejected on /chat (H1)."""
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    sess = await client.post(
        "/api/v1/widget/session",
        json={"visitor_key": "sec-guest-1", "title": "t"},
    )
    assert sess.status_code == 201, sess.text
    token = sess.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Full chat surface should be forbidden for guest tokens
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={"title": "hack"},
    )
    assert conv.status_code == 403
    assert "guest" in conv.text.lower() or conv.json().get("detail") == "guest_scope_violation"
