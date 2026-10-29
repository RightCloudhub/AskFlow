import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Message } from "../api/types";
import { getToken } from "../api/client";
import { disposeChatSocket, getChatSocket } from "../services/chat-ws";
import { prepareMallSession } from "../mall/session";
import { useFeatures } from "../plugins/features";
import { ChatKeys } from "./query-keys";

async function prepareChat(active: boolean) {
  if (!active) return;
  const before = getToken();
  await prepareMallSession();
  if (before !== getToken()) disposeChatSocket();
}

export function useChatTransport(onHandoff: (summary: string) => void) {
  const qc = useQueryClient();
  const { enabled } = useFeatures();
  const [streamText, setStreamText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  async function send(content: string, conversationId: string | null) {
    if (!conversationId || streaming) return;
    setSendError(null);
    setStreaming(true);
    setStreamText("");
    const key = ChatKeys.messages(conversationId);
    const previous = qc.getQueryData<Message[]>(key) ?? [];
    const message: Message = { id: `tmp-u-${Date.now()}`, role: "user", content,
      created_at: new Date().toISOString() };
    qc.setQueryData<Message[]>(key, [...previous, message]);
    try {
      await prepareChat(enabled("mall_account"));
      await getChatSocket().sendMessage(conversationId, content, {
        onToken: (chunk) => setStreamText((text) => text + chunk),
        onHandoff: (payload) => onHandoff(String(payload.summary || "已进入人工接管队列")),
        onError: setSendError,
      });
      await qc.invalidateQueries({ queryKey: key });
      await qc.invalidateQueries({ queryKey: ChatKeys.conversations() });
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "发送失败");
      qc.setQueryData<Message[]>(key, previous);
    } finally {
      setStreaming(false);
      setStreamText("");
    }
  }
  return { send, streamText, streaming, sendError, setSendError };
}
