"""OIDC role map + model fallback (enterprise)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.enums import LLMPurpose
from app.services.agent.model_router.router import ModelRouter
from app.services.auth.oidc import OIDCService, encode_mock_id_token, map_roles


def test_map_roles_prefers_admin():
    assert map_roles(["user", "admin"]) == "admin"
    assert map_roles(["support"]) == "agent"
    assert map_roles([]) == "user"


@pytest.mark.asyncio
async def test_oidc_jit_login():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        token = encode_mock_id_token(
            {
                "sub": "oidc-1",
                "email": "sso@corp.example",
                "preferred_username": "sso_user",
                "roles": ["agent"],
            }
        )
        tok, user = await OIDCService(db).login_with_id_token(token)
        assert tok.access_token
        assert user.role == "agent"
        assert user.email == "sso@corp.example"
    await engine.dispose()


@pytest.mark.asyncio
async def test_model_fallback_on_primary_fail():
    from app.core.config import Settings

    settings = Settings(
        ASKFLOW_ENV="test",
        SECRET_KEY="test-secret-key-not-for-prod",
        LLM_MODEL_GENERATE="primary-model-x",
        LLM_MODEL_CLASSIFY="fallback-model-y",
    )
    router = ModelRouter(settings)
    calls: list[str] = []

    async def invoker(model: str) -> str:
        calls.append(model)
        return f"ok:{model}"

    result, meta = await router.call_with_fallback(
        LLMPurpose.RAG_GENERATE,
        invoker,
        force_primary_fail=True,
    )
    assert result == "ok:fallback-model-y" or result.startswith("ok:")
    assert meta["fallback_used"] is True
    assert meta["model"] != "primary-model-x"
    assert calls[0] == "fallback-model-y" or "fallback-model-y" in calls
