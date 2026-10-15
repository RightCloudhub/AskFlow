"""In-process registry of open WebSockets per conversation for proactive delivery (arch §4.1)."""


class WsRegistry:
    def __init__(self) -> None:
        self._by_conversation: dict[str, set] = {}

    def register(self, conversation_id: str, websocket) -> None:
        self._by_conversation.setdefault(conversation_id, set()).add(websocket)

    def unregister(self, conversation_id: str, websocket) -> None:
        sockets = self._by_conversation.get(conversation_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._by_conversation.pop(conversation_id, None)

    def unregister_all(self, websocket) -> None:
        for conversation_id in list(self._by_conversation):
            self.unregister(conversation_id, websocket)

    def count(self, conversation_id: str) -> int:
        return len(self._by_conversation.get(conversation_id, ()))

    async def broadcast(self, conversation_id: str, payload: dict) -> int:
        sent = 0
        for websocket in list(self._by_conversation.get(conversation_id, ())):
            try:
                await websocket.send_json(payload)
                sent += 1
            except Exception:  # noqa: BLE001 - a dead socket is simply dropped
                self.unregister(conversation_id, websocket)
        return sent


registry = WsRegistry()
