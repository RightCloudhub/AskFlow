import pytest

from app.core.config import Settings
from app.services.agent.loop.engine import LoopEngine


@pytest.mark.asyncio
async def test_unknown_tool():
    engine = LoopEngine({})
    r = await engine.run(tool_name="nope", arguments={})
    assert r.ok is False
    assert r.error_class == "unknown_tool"


@pytest.mark.asyncio
async def test_tool_retries_then_stop():
    calls = {"n": 0}

    async def flaky(_args):
        calls["n"] += 1
        return {"status": "error", "error_class": "timeout", "message": "timeout"}

    settings = Settings(ASKFLOW_ENV="test", SECRET_KEY="test-secret-key-not-for-prod")
    settings.max_retries_per_tool = 1
    settings.max_loop_steps = 6
    engine = LoopEngine({"t": flaky}, settings=settings)
    r = await engine.run(tool_name="t", arguments={})
    assert r.ok is False
    assert calls["n"] >= 2  # initial + retries
    assert r.error_class in {"tool_error", "timeout"} or r.phase.value == "recover"


@pytest.mark.asyncio
async def test_no_infinite_loop_on_persistent_error():
    calls = {"n": 0}

    async def always_fail(_args):
        calls["n"] += 1
        raise RuntimeError("boom")

    settings = Settings(
        ASKFLOW_ENV="test",
        SECRET_KEY="test-secret-key-not-for-prod",
        max_retries_per_tool=2,
        max_loop_steps=6,
        max_tool_calls=4,
    )
    engine = LoopEngine({"t": always_fail}, settings=settings)
    r = await engine.run(tool_name="t", arguments={})
    assert r.ok is False
    assert calls["n"] <= settings.max_tool_calls + 1
