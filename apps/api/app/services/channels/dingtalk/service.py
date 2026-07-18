"""DingTalk (钉钉) inbound webhook + same Agent pipeline (PRD E7b deferred)."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.services.channels.pipeline import run_channel_turn

CHANNEL = "dingtalk"


@dataclass
class DingTalkHandleResult:
    kind: str  # challenge | message | ignored
    challenge: str | None = None
    reply_text: str | None = None
    run_id: str | None = None
    route: str | None = None
    reply_status: str | None = None


class DingTalkService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def verify_sign(self, timestamp: str | None, sign: str | None) -> bool:
        secret = self.settings.dingtalk_app_secret
        if not secret:
            return not self.settings.is_production_like
        if not timestamp or not sign:
            return False
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        import base64

        expected = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(expected, sign)

    def parse_message(self, body: dict[str, Any]) -> tuple[str, str] | None:
        # Stream / robot callback shapes
        if body.get("type") == "check_url" or body.get("challenge"):
            return None
        text = ""
        text_obj = body.get("text") or {}
        if isinstance(text_obj, dict):
            text = str(text_obj.get("content") or "").strip()
        if not text:
            text = str(body.get("content") or body.get("textContent") or "").strip()
        # attachment cue
        if not text and body.get("msgtype") in {"picture", "file", "richText"}:
            text = f"[attachment type={body.get('msgtype')}]"
        sender = body.get("senderStaffId") or body.get("senderId") or body.get("userid") or ""
        if not sender or not text:
            return None
        return str(sender), text

    async def handle_payload(
        self,
        body: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> DingTalkHandleResult:
        h = {k.lower(): v for k, v in (headers or {}).items()}
        if body.get("challenge") or body.get("type") == "check_url":
            return DingTalkHandleResult(
                kind="challenge",
                challenge=str(body.get("challenge") or "ok"),
            )
        if not self.verify_sign(h.get("timestamp"), h.get("sign")):
            return DingTalkHandleResult(kind="ignored", reply_status="bad_token")

        parsed = self.parse_message(body)
        if parsed is None:
            return DingTalkHandleResult(kind="ignored")
        uid, text = parsed
        turn = await run_channel_turn(
            self.db,
            channel=CHANNEL,
            external_user_id=uid,
            text=text,
            chat_key=str(body.get("conversationId") or uid),
            title_prefix="钉钉",
        )
        return DingTalkHandleResult(
            kind="message",
            reply_text=turn.answer,
            run_id=turn.run_id,
            route=turn.route,
            reply_status="local_only",
        )
