"""Chat turn orchestration split into preparation, processing and persistence."""

from dataclasses import dataclass

from app.models.enums import MessageRole
from app.plugins.types import ChatTurnContext
from app.services.agent.intake.chat import maybe_create_goal_task
from app.services.agent.pipeline.runner import MessagePipeline
from app.services.bots.profiles import get_bot
from app.services.chat.attachments import attachment_prompt_suffix, normalize_attachments
from app.services.chat.side_effects.apply import apply_side_effects
from app.utils.merge import merge_patch

TITLE_MAX = 40
TITLE_DEFAULTS = frozenset({"新会话", "New chat"})


@dataclass
class ChatInput:
    conversation_id: str
    user_id: str
    content: str
    attachments: list | None = None
    bot_id: str | None = None
    locale: str | None = None


class ChatTurn:
    def __init__(self, service, request: ChatInput):
        self.service, self.request = service, request

    async def run(self):
        req = self.request
        conv = await self.service.get_conversation(req.conversation_id, req.user_id)
        text, user_meta = self._payload()
        user_msg = await self.service.add_message(
            conv.id, role=MessageRole.USER.value, content=text, meta=user_meta or None
        )
        rows = await self.service.list_messages(conv.id, req.user_id)
        history = [{"role": m.role, "content": m.content} for m in rows if m.id != user_msg.id]
        result = await self._process(conv, text=text, history=history)
        if result.metadata_patch:
            conv.metadata_json = merge_patch(conv.metadata_json or {}, result.metadata_patch)
        result.side_effects = await self._effects(result)
        assistant = await self.service.add_message(
            conv.id,
            role=MessageRole.ASSISTANT.value,
            content=result.answer,
            meta=self._response_meta(result),
        )
        if conv.title in TITLE_DEFAULTS and req.content:
            conv.title = req.content[:TITLE_MAX]
        await self.service.db.flush()
        return user_msg, assistant, result

    def _payload(self):
        req = self.request
        attachments = normalize_attachments(req.attachments)
        meta = {}
        if attachments:
            meta["attachments"] = attachments
        if req.bot_id:
            meta["bot_id"] = req.bot_id
        if req.locale:
            meta["locale"] = req.locale
        return req.content + attachment_prompt_suffix(attachments), meta

    def _metadata(self, conv):
        req = self.request
        meta = dict(conv.metadata_json or {})
        bot = get_bot(req.bot_id or meta.get("bot_id"))
        meta.setdefault("bot_id", bot.id)
        if req.locale:
            meta["locale"] = req.locale
        elif bot.locale:
            meta.setdefault("locale", bot.locale)
        meta["system_prompt_key"] = bot.system_prompt_key
        if bot.knowledge_tags:
            meta["knowledge_tags"] = bot.knowledge_tags
        return meta

    async def _process(self, conv, *, text, history):
        meta = self._metadata(conv)
        result = await maybe_create_goal_task(
            self.service.db, conv, text=text, history=history, metadata=meta
        )
        if result is not None:
            return result
        return await MessagePipeline(self.service.db).handle(
            text,
            history=history,
            metadata=meta,
            conversation_status=conv.status,
            cancel_key=conv.id,
        )

    async def _effects(self, result):
        req = self.request
        return await apply_side_effects(
            dict(result.side_effects or {}),
            ChatTurnContext(
                db=self.service.db,
                conversation_id=req.conversation_id,
                user_id=req.user_id,
                content=req.content,
                intent=result.intent,
                route=result.route,
                refused=result.refused,
                verification=result.verification if isinstance(result.verification, dict) else None,
                run_id=result.run_id,
                cost=result.cost if isinstance(result.cost, dict) else None,
                flags=list(result.flags or []),
            ),
        )

    @staticmethod
    def _response_meta(result):
        fields = (
            "run_id",
            "trace_id",
            "route",
            "intent",
            "confidence",
            "answer_confidence",
            "sources",
            "flags",
            "verification",
            "rewrite",
            "refused",
            "side_effects",
            "cost",
        )
        meta = {name: getattr(result, name) for name in fields}
        meta["models"] = result.cost.get("entries") if isinstance(result.cost, dict) else []
        return meta
