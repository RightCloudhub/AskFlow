"""Canonical inbound message shared by every channel adapter (arch §10.1)."""

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CanonicalMessage:
    channel: str
    channel_message_id: str
    channel_user_id: str
    session_key: str
    text: str
    chat_key: str | None = None
    reply_to: str | None = None
    raw: dict = field(default_factory=dict)

    def to_payload(self) -> dict:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict) -> "CanonicalMessage":
        return cls(
            channel=str(payload["channel"]),
            channel_message_id=str(payload["channel_message_id"]),
            channel_user_id=str(payload["channel_user_id"]),
            session_key=str(payload["session_key"]),
            text=str(payload["text"]),
            chat_key=payload.get("chat_key"),
            reply_to=payload.get("reply_to"),
            raw=dict(payload.get("raw") or {}),
        )


def session_key_for(*, channel: str, chat_key: str | None, user_id: str) -> str:
    return f"{channel}:{chat_key or user_id}"
