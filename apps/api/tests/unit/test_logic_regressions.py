"""Critical-path logic regressions (isolation, OIDC, agent_run, Feishu gate)."""

from __future__ import annotations

import json
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.core.security import hash_password
from app.models.enums import HandoffStatus, UserRole
from app.models.handoff import HandoffSession
from app.models.user import User
from app.plugins.types import ChatTurnContext
from app.services.agent.cost.ledger import CostLedger
from app.services.agent.run_store import AgentRunStore
from app.services.auth.jwks import JWKSValidator
from app.services.auth.oidc import OIDCService
from app.services.channels.feishu.service import FeishuService
from app.services.chat.side_effects.agent_run import AgentRunSideEffect
from app.services.chat.side_effects.cost import CostSideEffect
from app.services.handoff.service import HandoffService
from app.services.widget.service import WidgetService, sanitize_visitor_key
from app.utils.ids import new_run_id

ISSUER = "https://idp.logic.test"
AUDIENCE = "askflow-logic"
KID = "logic-key"


async def _db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


def test_sanitize_visitor_key_strips_injection():
    assert "@" not in sanitize_visitor_key("evil@x.com")
    assert " " not in sanitize_visitor_key("a b")
    assert sanitize_visitor_key("ok-key_1") == "ok-key_1"
    assert len(sanitize_visitor_key("x" * 200)) <= 48


def test_feishu_fail_closed_without_token_in_production():
    settings = Settings(
        ASKFLOW_ENV="production",
        SECRET_KEY="test-secret-key-not-for-prod-xx",
        FEISHU_VERIFICATION_TOKEN=None,
    )
    svc = FeishuService.__new__(FeishuService)
    svc.settings = settings
    assert svc.verify_token(None) is False
    assert svc.verify_token("anything") is False

    dev = Settings(
        ASKFLOW_ENV="development",
        SECRET_KEY="test-secret-key-not-for-prod-xx",
        FEISHU_VERIFICATION_TOKEN=None,
    )
    svc.settings = dev
    assert svc.verify_token(None) is True


def test_oidc_jwks_rejects_bad_signature_and_wrong_aud():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()

    def _b64int(n: int) -> str:
        import base64

        length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(length, "big")).decode("ascii").rstrip("=")

    jwk = {
        "kty": "RSA",
        "kid": KID,
        "use": "sig",
        "alg": "RS256",
        "n": _b64int(public_numbers.n),
        "e": _b64int(public_numbers.e),
    }
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    now = int(time.time())
    v = JWKSValidator(issuer=ISSUER, audience=AUDIENCE, jwks_override={"keys": [jwk]})
    bad_sig = jwt.encode(
        {"sub": "u", "iss": ISSUER, "aud": AUDIENCE, "exp": now + 600, "iat": now},
        other_pem,
        algorithm="RS256",
        headers={"kid": KID},
    )
    with pytest.raises(ValueError):
        v.verify_id_token(bad_sig)
    wrong_aud = jwt.encode(
        {"sub": "u", "iss": ISSUER, "aud": "other", "exp": now + 600, "iat": now},
        pem,
        algorithm="RS256",
        headers={"kid": KID},
    )
    with pytest.raises(ValueError, match="invalid_claims"):
        v.verify_id_token(wrong_aud)
    expired = jwt.encode(
        {"sub": "u", "iss": ISSUER, "aud": AUDIENCE, "exp": now - 10, "iat": now - 100},
        pem,
        algorithm="RS256",
        headers={"kid": KID},
    )
    with pytest.raises(ValueError, match="token_expired"):
        v.verify_id_token(expired)


@pytest.mark.asyncio
async def test_widget_isolation_and_sanitize_roundtrip():
    engine, factory = await _db()
    async with factory() as db:
        a = await WidgetService(db).open_session(visitor_key="va@evil")
        b = await WidgetService(db).open_session(visitor_key="vb")
        assert a.visitor_key == "va_evil"
        assert a.user_id != b.user_id
        from app.services.chat.session.service import ChatService
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as ei:
            await ChatService(db).list_messages(a.conversation_id, b.user_id)
        assert ei.value.status_code == 403
    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_run_persists_after_side_effect():
    engine, factory = await _db()
    run_id = new_run_id()
    async with factory() as db:
        user = User(
            username="logic_u",
            email="logic@e.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER.value,
        )
        db.add(user)
        await db.flush()
        ledger = CostLedger(run_id)
        ledger.record(purpose="rag_generate", model="gpt-4o-mini", prompt_tokens=10, completion_tokens=5)
        cost = ledger.summary()
        turn = ChatTurnContext(
            db=db,
            conversation_id="c1",
            user_id=user.id,
            content="q",
            intent="faq",
            route="rag",
            refused=False,
            verification=None,
            run_id=run_id,
            cost=cost,
            flags=["ok"],
        )
        se = await CostSideEffect().apply({}, turn)
        se = await AgentRunSideEffect().apply(se, turn)
        assert se.get("agent_run_saved") is True
        row = await AgentRunStore(db).get_by_run_id(run_id)
        assert row is not None
        assert row.route == "rag"
        assert any(s.get("kind") == "route" for s in (row.steps or []))
    await engine.dispose()


@pytest.mark.asyncio
async def test_handoff_claim_returns_claimed_fields():
    engine, factory = await _db()
    async with factory() as db:
        user = User(
            username="hu",
            email="hu@e.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER.value,
        )
        agent = User(
            username="ha",
            email="ha@e.com",
            hashed_password=hash_password("password123"),
            role=UserRole.AGENT.value,
        )
        db.add_all([user, agent])
        await db.flush()
        from app.models.conversation import Conversation

        conv = Conversation(user_id=user.id, title="h")
        db.add(conv)
        await db.flush()
        hs = HandoffSession(
            conversation_id=conv.id,
            user_id=user.id,
            status=HandoffStatus.QUEUED.value,
            summary="s",
            intent="handoff",
        )
        db.add(hs)
        await db.flush()
        claimed = await HandoffService(db).claim(hs.id, agent.id)
        assert claimed.status == HandoffStatus.CLAIMED.value
        assert claimed.claimed_by == agent.id
        assert claimed.claimed_at is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_feishu_two_open_ids_isolated_users():
    engine, factory = await _db()
    async with factory() as db:
        settings = Settings(
            ASKFLOW_ENV="test",
            SECRET_KEY="test-secret-key-not-for-prod-xx",
        )
        svc = FeishuService(db, settings=settings)

        async def handle(oid: str, text: str):
            body = {
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "sender": {"sender_id": {"open_id": oid}},
                    "message": {
                        "message_id": f"om_{oid}",
                        "chat_id": f"oc_{oid}",
                        "message_type": "text",
                        "content": json.dumps({"text": text}),
                    },
                },
            }
            return await svc.handle_payload(body)

        r1 = await handle("ou_a", "你好")
        r2 = await handle("ou_b", "你好")
        assert r1.kind == "message" and r2.kind == "message"
        from app.models.user import User as U
        from sqlalchemy import select

        users = (
            await db.execute(select(U).where(U.email.like("feishu.%@channel.askflow.local")))
        ).scalars().all()
        assert len(users) >= 2
        ids = {u.id for u in users}
        assert len(ids) >= 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_oidc_mock_not_used_on_staging_without_mock_flag():
    """Production path requires JWKS; mock tokens must not silently succeed."""
    engine, factory = await _db()
    async with factory() as db:
        settings = Settings(
            ASKFLOW_ENV="staging",
            SECRET_KEY="test-secret-key-not-for-prod-xx",
            OIDC_ISSUER=ISSUER,
            OIDC_CLIENT_ID=AUDIENCE,
            OIDC_MOCK=False,
        )
        from app.services.auth.oidc import encode_mock_id_token

        mock = encode_mock_id_token(
            {"sub": "x", "email": "x@y.com", "preferred_username": "x", "roles": ["user"]}
        )
        with pytest.raises(ValueError):
            await OIDCService(db, settings=settings).login_with_id_token(mock)
    await engine.dispose()
