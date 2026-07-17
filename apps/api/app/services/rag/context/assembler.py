"""History + evidence assembly with budget (PRD §4.15 / context-engineering)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings


@dataclass
class ContextBundle:
    messages: list[dict[str, str]]
    evidence_block: str
    flags: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)


class ContextAssembler:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def assemble(
        self,
        *,
        question: str,
        history: list[dict[str, str]],
        sources: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> ContextBundle:
        flags: list[str] = []
        system = system_prompt or (
            "你是企业智能客服助手。仅依据提供的证据回答，不知则说明不确定。"
            "引用证据时使用 [n] 标注，n 对应该条来源编号。"
        )
        evidence_lines = []
        for s in sources:
            idx = s.get("index", 0)
            src = s.get("source", "unknown")
            text = s.get("text", "")
            evidence_lines.append(f"[{idx}] ({src}) {text}")
        evidence_block = "\n".join(evidence_lines)

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        # history already budgeted by harness
        messages.extend(history)
        user_content = f"证据：\n{evidence_block}\n\n用户问题：{question}"
        messages.append({"role": "user", "content": user_content})

        trace = {
            "history_msgs": len(history),
            "evidence_count": len(sources),
            "evidence_chars": len(evidence_block),
        }
        return ContextBundle(messages=messages, evidence_block=evidence_block, flags=flags, trace=trace)
