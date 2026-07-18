"""Multi-step tool loop: plan → act → observe → recover (PRD §4.13)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.core.config import Settings, get_settings
from app.models.enums import LoopPhase

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class LoopResult:
    ok: bool
    phase: LoopPhase
    output: dict[str, Any] = field(default_factory=dict)
    steps: int = 0
    tool_calls: int = 0
    message: str | None = None
    error_class: str | None = None


class LoopEngine:
    def __init__(
        self,
        tools: dict[str, ToolHandler],
        settings: Settings | None = None,
    ) -> None:
        self.tools = tools
        self.settings = settings or get_settings()

    async def run(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        plan_hint: str | None = None,
        intent: str | None = None,
    ) -> LoopResult:
        _ = plan_hint
        from app.services.agent.reasoning import reasoning_extra_steps
        from app.services.sandbox.guard import sandbox_allowed

        started = time.monotonic()
        steps = 0
        tool_calls = 0
        retries = 0
        extra = reasoning_extra_steps(intent)
        max_steps = self.settings.max_loop_steps + extra

        if tool_name.startswith("sandbox_") and not sandbox_allowed():
            return LoopResult(
                ok=False,
                phase=LoopPhase.RECOVER,
                message="sandbox_disabled",
                error_class="sandbox_disabled",
            )

        if tool_name not in self.tools:
            return LoopResult(
                ok=False,
                phase=LoopPhase.PLAN,
                message=f"工具 {tool_name} 未注册",
                error_class="unknown_tool",
            )

        while steps < max_steps:
            steps += 1
            elapsed_ms = (time.monotonic() - started) * 1000
            if elapsed_ms > self.settings.max_wall_ms:
                return LoopResult(
                    ok=False,
                    phase=LoopPhase.RECOVER,
                    steps=steps,
                    tool_calls=tool_calls,
                    message="处理超时，请稍后重试或转人工。",
                    error_class="wall_timeout",
                )

            if tool_calls >= self.settings.max_tool_calls:
                return LoopResult(
                    ok=False,
                    phase=LoopPhase.RECOVER,
                    steps=steps,
                    tool_calls=tool_calls,
                    message="工具调用次数已达上限。",
                    error_class="tool_budget",
                )

            # ACT
            tool_calls += 1
            try:
                result = await self.tools[tool_name](arguments)
            except Exception as exc:  # recover
                retries += 1
                if retries > self.settings.max_retries_per_tool:
                    return LoopResult(
                        ok=False,
                        phase=LoopPhase.RECOVER,
                        steps=steps,
                        tool_calls=tool_calls,
                        message="工具执行失败，请稍后重试。",
                        error_class="tool_error",
                        output={"error": str(exc)},
                    )
                continue

            # OBSERVE
            status = str(result.get("status", "ok"))
            if status in {"ok", "mock"}:
                return LoopResult(
                    ok=True,
                    phase=LoopPhase.FINALIZE,
                    steps=steps,
                    tool_calls=tool_calls,
                    output=result,
                )

            error_class = str(result.get("error_class", "unknown"))
            # do not blind-retry 4xx / auth
            if error_class in {"http_4xx", "auth", "bad_params"}:
                return LoopResult(
                    ok=False,
                    phase=LoopPhase.OBSERVE,
                    steps=steps,
                    tool_calls=tool_calls,
                    output=result,
                    error_class=error_class,
                    message=result.get("message") or "工具参数或权限错误。",
                )
            retries += 1
            if retries > self.settings.max_retries_per_tool:
                return LoopResult(
                    ok=False,
                    phase=LoopPhase.RECOVER,
                    steps=steps,
                    tool_calls=tool_calls,
                    output=result,
                    error_class=error_class,
                    message="工具多次失败，已停止重试。",
                )

        return LoopResult(
            ok=False,
            phase=LoopPhase.RECOVER,
            steps=steps,
            tool_calls=tool_calls,
            message="步骤预算已用尽，请澄清需求或转人工。",
            error_class="step_budget",
        )
