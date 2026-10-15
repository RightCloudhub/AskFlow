"""Process one claimed inbox row through the shared pipeline, then reply (arch §9.1)."""

from app.core.config import Settings
from app.services.channels.canonical import CanonicalMessage
from app.services.channels.pipeline import run_channel_turn
from app.services.outbound.senders import get_sender

TITLE_PREFIXES = {"feishu": "飞书", "wecom": "企微", "dingtalk": "钉钉"}
STATUS_LOCAL_ONLY = "local_only"


async def process_canonical(db, message: CanonicalMessage, settings: Settings) -> str:
    """Run the canonical message through the same chat pipeline as every channel."""
    result = await run_channel_turn(
        db,
        channel=message.channel,
        external_user_id=message.channel_user_id,
        text=message.text,
        chat_key=message.chat_key,
        title_prefix=TITLE_PREFIXES.get(message.channel),
    )
    return await _reply(db, message=message, answer=result.answer, settings=settings)


async def _reply(db, *, message: CanonicalMessage, answer: str, settings: Settings) -> str:
    if message.channel == "feishu":
        return await _reply_feishu(db, message=message, answer=answer, settings=settings)
    sender = get_sender(message.channel)
    if sender is None:
        return STATUS_LOCAL_ONLY
    return await sender(target=message.chat_key or message.channel_user_id, text=answer)


async def _reply_feishu(db, *, message: CanonicalMessage, answer: str, settings: Settings) -> str:
    from app.services.channels.feishu.service import FeishuService
    from app.services.outbound.senders import send_feishu

    if message.reply_to and settings.feishu_app_id:
        return await FeishuService(db, settings).reply_to_message(message.reply_to, answer)
    if message.chat_key:
        return await send_feishu(target=message.chat_key, text=answer, settings=settings)
    return STATUS_LOCAL_ONLY
