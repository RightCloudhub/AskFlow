"""TOOL route — order lookup via loop + slots."""

from __future__ import annotations

from app.models.enums import Intent, Route
from app.services.agent.pipeline.context import PipelineResult, TurnContext

ORDER_SLOT_PROMPT = "请提供您的订单号（例如 ORD202401010001），以便查询物流与状态。"


async def handle_tool(ctx: TurnContext) -> PipelineResult:
    order_id = ctx.order_id or ctx.slots.extract_order_id(ctx.text)
    if not order_id:
        patch = ctx.slots.start_order_slot(ctx.metadata)
        final = ctx.harness.finalize(ORDER_SLOT_PROMPT)
        intent = (
            ctx.intent_result.intent.value
            if ctx.intent_result
            else Intent.ORDER_QUERY.value
        )
        confidence = ctx.intent_result.confidence if ctx.intent_result else 0.9
        return PipelineResult(
            run_id=ctx.run_id,
            trace_id=ctx.trace_id,
            answer=final.text,
            route=Route.TOOL.value,
            intent=intent,
            confidence=confidence,
            flags=list(ctx.flags) + ["slot_start"],
            metadata_patch=patch,
            side_effects=dict(ctx.side_effects),
            cost=ctx.ledger.summary(),
        )
    return await _run_order_lookup(ctx, order_id)


async def _run_order_lookup(ctx: TurnContext, order_id: str) -> PipelineResult:
    loop = ctx.loop
    if loop is None:
        from app.services.agent.loop.engine import LoopEngine
        from app.services.tools.registry import registry

        loop = LoopEngine(registry.as_loop_map())
    intent = (
        ctx.intent_result.intent.value if ctx.intent_result else Intent.ORDER_QUERY.value
    )
    loop_result = await loop.run(
        tool_name="search_order",
        arguments={"order_id": order_id},
        intent=intent,
    )
    answer, extra_flags = _format_order_answer(order_id, loop_result)
    final = ctx.harness.finalize(answer)
    confidence = ctx.intent_result.confidence if ctx.intent_result else 0.9
    se = {
        **ctx.side_effects,
        "tool": {
            "name": "search_order",
            "order_id": order_id,
            "loop_steps": loop_result.steps,
            "ok": loop_result.ok,
        },
    }
    return PipelineResult(
        run_id=ctx.run_id,
        trace_id=ctx.trace_id,
        answer=final.text,
        route=Route.TOOL.value,
        intent=intent,
        confidence=confidence,
        flags=list(ctx.flags) + final.flags + extra_flags,
        metadata_patch=dict(ctx.meta_patch),
        side_effects=se,
        cost=ctx.ledger.summary(),
    )


def _format_order_answer(order_id: str, loop_result: object) -> tuple[str, list[str]]:
    ok = getattr(loop_result, "ok", False)
    output = getattr(loop_result, "output", {}) or {}
    if not ok:
        return getattr(loop_result, "message", None) or "订单查询失败。", []
    data = output.get("data") or {}
    source = output.get("data_source", "unknown")
    answer = (
        f"订单 {order_id} 查询结果（来源：{source}）：\n"
        f"- 状态：{data.get('status', 'unknown')}\n"
        f"- 承运商：{data.get('carrier', '-')}\n"
        f"- 运单号：{data.get('tracking', '-')}\n"
        f"- ETA：{data.get('eta', '-')}"
    )
    flags: list[str] = []
    if source == "mock":
        answer += f"\n（说明：当前为降级 mock 数据，原因：{output.get('mock_reason', '')}）"
        flags.append("tool_mock")
    return answer, flags
