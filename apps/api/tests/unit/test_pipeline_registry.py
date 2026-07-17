"""Pipeline dispatches via route handler registry (not if/else monolith)."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.plugins.context import AppContext
from app.plugins.loader import load_plugins
from app.plugins.runtime import set_app_context
from app.services.agent.pipeline.runner import MessagePipeline

ORDER_ID_TEXT = "请查一下订单 ORD202401010001 的物流状态"


@pytest.mark.asyncio
async def test_missing_handler_degrades_to_clarify_without_crash() -> None:
    """Disabled capability: empty registry → safe clarify, no invented domain data."""
    settings = get_settings()
    empty = AppContext(settings=settings, features=frozenset({"core"}))
    empty.route_handlers = {}
    set_app_context(empty)
    try:
        pr = await MessagePipeline().handle("退货政策是什么？")
        assert pr.answer
        assert pr.route == "clarify"
        assert any(f.startswith("handler_missing:") for f in pr.flags)
        se = pr.side_effects or {}
        assert "ticket" not in se
        assert "handoff" not in se
        assert "tool" not in se
    finally:
        set_app_context(None)


@pytest.mark.asyncio
async def test_core_only_order_id_does_not_run_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC2: core-only profile must not invent mock order data for order-id text.

    Drives real MessagePipeline.handle with real load_plugins(core-only).
    """
    monkeypatch.setenv("ASKFLOW_PROFILE", "core-only")
    get_settings.cache_clear()
    set_app_context(None)
    ctx = load_plugins(get_settings())
    assert "tools" not in ctx.features
    assert "tool" not in ctx.route_handlers
    try:
        pr = await MessagePipeline().handle(ORDER_ID_TEXT)
        assert pr.route != "tool", f"tools disabled but route={pr.route}"
        se = pr.side_effects or {}
        assert "tool" not in se, f"invented tool side_effect: {se.get('tool')}"
        # Safe degrade: clarify after missing handlers, or classify without tools
        assert pr.route in {"clarify", "rag", "refuse", "blocked"}
        if pr.route == "clarify":
            assert any(
                f.startswith("handler_missing:") or f == "tools_disabled_skip_slot"
                for f in pr.flags
            )
        # Must not look like mock order payload
        assert "承运商" not in pr.answer
        assert "mock" not in pr.answer.lower()
    finally:
        set_app_context(None)
        monkeypatch.setenv("ASKFLOW_PROFILE", "full")
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_empty_registry_order_id_no_tool_side_effects() -> None:
    """Order-id path must use registry; missing tool handler → no tool SE."""
    settings = get_settings()
    empty = AppContext(settings=settings, features=frozenset({"core"}))
    empty.route_handlers = {}
    set_app_context(empty)
    try:
        pr = await MessagePipeline().handle(ORDER_ID_TEXT)
        assert pr.route != "tool"
        assert "tool" not in (pr.side_effects or {})
        assert "承运商" not in pr.answer
    finally:
        set_app_context(None)


@pytest.mark.asyncio
async def test_full_handlers_dispatch_rag_for_faq() -> None:
    """With defaults (no AppContext), FAQ text hits real RAG handler path."""
    set_app_context(None)
    pr = await MessagePipeline().handle("如何申请退货？")
    assert pr.route in {"rag", "clarify", "refuse"}
    assert pr.run_id
    assert pr.cost is not None


@pytest.mark.asyncio
async def test_out_of_scope_uses_refuse_handler() -> None:
    set_app_context(None)
    pr = await MessagePipeline().handle("请给我癌症治疗方案和处方建议")
    assert pr.route == "refuse"
    assert pr.refused is True
    assert pr.intent == "out_of_scope"


@pytest.mark.asyncio
async def test_full_profile_order_id_uses_tool_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity: full profile still runs tool path for order ids (not a false pass)."""
    monkeypatch.setenv("ASKFLOW_PROFILE", "full")
    get_settings.cache_clear()
    set_app_context(None)
    load_plugins(get_settings())
    try:
        pr = await MessagePipeline().handle(ORDER_ID_TEXT)
        assert pr.route == "tool"
        assert (pr.side_effects or {}).get("tool", {}).get("name") == "search_order"
    finally:
        set_app_context(None)
