"""Feishu bot inbound events + optional reply (PRD E7b / U-12)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.middleware.metrics import CHAT_TURNS
from app.services.audit.logger.service import AuditService
from app.services.channels.identity import ensure_channel_user, open_channel_conversation
from app.services.chat.session.service import ChatService

CHANNEL = "feishu"
HTTP_TIMEOUT_SEC = 10.0
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
REPLY_URL = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"

HttpPost = Callable[..., Awaitable[httpx.Response]]


@dataclass
class FeishuInbound:
    open_id: str
    text: str
    message_id: str | None
    chat_id: str | None
    raw_event: str


@dataclass
class FeishuHandleResult:
    kind: str  # challenge | message | ignored
    challenge: str | None = None
    reply_text: str | None = None
    run_id: str | None = None
    route: str | None = None
    reply_status: str | None = None


class FeishuService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
        *,
        http_post: HttpPost | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self._http_post = http_post

    def verify_token(self, token: str | None) -> bool:
        expected = self.settings.feishu_verification_token
        if not expected:
            # Dev/test: accept when token not configured
            return True
        return bool(token) and token == expected

    def parse_event(self, body: dict[str, Any]) -> FeishuInbound | str | None:
        """Return challenge str, FeishuInbound, or None if ignore."""
        if body.get("type") == "url_verification" or body.get("challenge"):
            return str(body.get("challenge") or "")
        # Event v2
        header = body.get("header") or {}
        event = body.get("event") or {}
        if header.get("event_type") == "im.message.receive_v1" or event.get("message"):
            return self._parse_v2(event)
        # Legacy message
        if event.get("type") == "message" or body.get("type") == "event_callback":
            return self._parse_legacy(event if event else body)
        return None

    def _parse_v2(self, event: dict[str, Any]) -> FeishuInbound | None:
        msg = event.get("message") or {}
        sender = event.get("sender") or {}
        sid = sender.get("sender_id") or {}
        open_id = str(sid.get("open_id") or sid.get("user_id") or "")
        if not open_id:
            return None
        text = self._extract_text(msg.get("content") or "", msg.get("message_type") or "text")
        if not text:
            return None
        return FeishuInbound(
            open_id=open_id,
            text=text,
            message_id=msg.get("message_id"),
            chat_id=msg.get("chat_id"),
            raw_event="im.message.receive_v1",
        )

    def _parse_legacy(self, event: dict[str, Any]) -> FeishuInbound | None:
        open_id = str(event.get("open_id") or event.get("user_open_id") or "")
        text = str(event.get("text") or event.get("text_without_at_bot") or "").strip()
        if not open_id or not text:
            return None
        return FeishuInbound(
            open_id=open_id,
            text=text,
            message_id=event.get("message_id") or event.get("open_message_id"),
            chat_id=event.get("chat_id") or event.get("open_chat_id"),
            raw_event="legacy.message",
        )

    def _extract_text(self, content: str, message_type: str) -> str:
        if message_type != "text":
            return ""
        try:
            data = json.loads(content) if content else {}
            return str(data.get("text") or "").strip()
        except json.JSONDecodeError:
            return content.strip()

    async def handle_payload(self, body: dict[str, Any]) -> FeishuHandleResult:
        token = body.get("token") or (body.get("header") or {}).get("token")
        if not self.verify_token(token if isinstance(token, str) else None):
            return FeishuHandleResult(kind="ignored", reply_status="bad_token")

        parsed = self.parse_event(body)
        if isinstance(parsed, str):
            return FeishuHandleResult(kind="challenge", challenge=parsed)
        if parsed is None:
            return FeishuHandleResult(kind="ignored")

        return await self._handle_message(parsed)

    async def _handle_message(self, inbound: FeishuInbound) -> FeishuHandleResult:
        user = await ensure_channel_user(
            self.db, channel=CHANNEL, external_id=inbound.open_id
        )
        chat_key = inbound.chat_id or inbound.open_id
        conv = await open_channel_conversation(
            self.db,
            user_id=user.id,
            title=f"飞书:{inbound.open_id[:12]}",
            external_chat_key=chat_key,
        )
        _user_msg, asst_msg, result = await ChatService(self.db).handle_user_message(
            conv.id, user.id, inbound.text
        )
        CHAT_TURNS.labels(route=result.route, intent=result.intent or "none").inc()
        await AuditService(self.db).log(
            action="feishu.message",
            resource_type="conversation",
            resource_id=conv.id,
            actor_id=user.id,
            detail={
                "open_id": inbound.open_id,
                "run_id": result.run_id,
                "route": result.route,
            },
        )
        reply_status = "local_only"
        if inbound.message_id and self.settings.feishu_app_id:
            reply_status = await self.reply_to_message(inbound.message_id, asst_msg.content)
        return FeishuHandleResult(
            kind="message",
            reply_text=asst_msg.content,
            run_id=result.run_id,
            route=result.route,
            reply_status=reply_status,
        )

    async def reply_to_message(self, message_id: str, text: str) -> str:
        token = await self._tenant_token()
        if not token:
            return "no_token"
        url = REPLY_URL.format(message_id=message_id)
        payload = {
            "content": json.dumps({"text": text[:4000]}, ensure_ascii=False),
            "msg_type": "text",
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            if self._http_post:
                resp = await self._http_post(url, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC) as client:
                    resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                return f"http_{resp.status_code}"
            data = resp.json() if resp.content else {}
            if data.get("code") not in (0, None):
                return f"api_{data.get('code')}"
            return "sent"
        except Exception as exc:
            return f"error:{str(exc)[:80]}"

    async def _tenant_token(self) -> str | None:
        app_id = self.settings.feishu_app_id
        secret = self.settings.feishu_app_secret
        if not app_id or not secret:
            return None
        body = {"app_id": app_id, "app_secret": secret}
        try:
            if self._http_post:
                resp = await self._http_post(TOKEN_URL, json=body)
            else:
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC) as client:
                    resp = await client.post(TOKEN_URL, json=body)
            if resp.status_code >= 400:
                return None
            data = resp.json()
            return data.get("tenant_access_token")
        except Exception:
            return None
