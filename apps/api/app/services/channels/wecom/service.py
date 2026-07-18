"""WeCom (企业微信) inbound webhook + same Agent pipeline (PRD E7b deferred)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.services.channels.pipeline import run_channel_turn

CHANNEL = "wecom"


@dataclass
class WeComHandleResult:
    kind: str  # echo | message | ignored
    echo_str: str | None = None
    reply_text: str | None = None
    run_id: str | None = None
    route: str | None = None
    reply_status: str | None = None


class WeComService:
    """Supports URL verification + JSON text message body (simplified Open API)."""

    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def verify_url(
        self,
        *,
        msg_signature: str | None,
        timestamp: str | None,
        nonce: str | None,
        echostr: str | None,
    ) -> str | None:
        """Return echostr when token check passes (plain mode / test)."""
        token = self.settings.wecom_token
        if not echostr:
            return None
        if not token:
            return echostr if not self.settings.is_production_like else None
        if not msg_signature or not timestamp or not nonce:
            return None
        items = sorted([token, str(timestamp), str(nonce), str(echostr)])
        digest = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
        if digest != msg_signature:
            return None
        return echostr

    def parse_message(self, body: dict[str, Any]) -> tuple[str, str] | None:
        """Extract (user_id, text) from simplified JSON callback."""
        # Compatible shapes: MsgType/text, or content/from
        msg_type = str(body.get("MsgType") or body.get("msgtype") or "text").lower()
        if msg_type not in {"text", "text_msg"}:
            # E16: image → synthetic text cue
            if msg_type in {"image", "file"}:
                uid = str(body.get("FromUserName") or body.get("from") or "")
                media = str(body.get("MediaId") or body.get("PicUrl") or body.get("url") or "")
                if uid and media:
                    return uid, f"[attachment type={msg_type} ref={media[:80]}]"
            return None
        uid = str(body.get("FromUserName") or body.get("from") or body.get("userid") or "")
        text = str(body.get("Content") or body.get("text") or body.get("content") or "").strip()
        if not uid or not text:
            return None
        return uid, text

    async def handle_payload(
        self,
        body: dict[str, Any],
        *,
        query: dict[str, str] | None = None,
    ) -> WeComHandleResult:
        q = query or {}
        if q.get("echostr"):
            echo = self.verify_url(
                msg_signature=q.get("msg_signature"),
                timestamp=q.get("timestamp"),
                nonce=q.get("nonce"),
                echostr=q.get("echostr"),
            )
            if echo is None:
                return WeComHandleResult(kind="ignored", reply_status="bad_token")
            return WeComHandleResult(kind="echo", echo_str=echo)

        token = self.settings.wecom_token
        if token and self.settings.is_production_like:
            # optional body token field
            if body.get("Token") and body.get("Token") != token:
                return WeComHandleResult(kind="ignored", reply_status="bad_token")

        parsed = self.parse_message(body)
        if parsed is None:
            return WeComHandleResult(kind="ignored")
        uid, text = parsed
        turn = await run_channel_turn(
            self.db,
            channel=CHANNEL,
            external_user_id=uid,
            text=text,
            chat_key=str(body.get("AgentID") or body.get("agentid") or uid),
            title_prefix="企微",
        )
        return WeComHandleResult(
            kind="message",
            reply_text=turn.answer,
            run_id=turn.run_id,
            route=turn.route,
            reply_status="local_only",
        )
