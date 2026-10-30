import { useCallback, useEffect, useRef, useState } from "react";
import { clearWidgetSession, getWidgetSession, widgetFetch, WidgetRequestError, WIDGET_AUTH_FAILURES, type WidgetMessage, type WidgetSession } from "./widget-service";

function useWidgetConnection() {
  const [session, setSession] = useState<WidgetSession>();
  const [messages, setMessages] = useState<WidgetMessage[]>([]);
  const [connecting, setConnecting] = useState(true);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const connect = useCallback(async () => {
    const request = ++generation.current;
    setConnecting(true); setError("");
    try {
      const current = await getWidgetSession();
      const history = await widgetFetch<WidgetMessage[]>(`/widget/conversations/${current.conversation_id}/messages`, { token: current.access_token });
      if (request !== generation.current) return;
      setSession(current);
      setMessages(history);
    } catch (error) {
      if (request !== generation.current) return;
      if (error instanceof WidgetRequestError && WIDGET_AUTH_FAILURES.has(error.status)) clearWidgetSession();
      setSession(undefined); setError("客服暂时无法连接，请重试连接。");
    } finally { if (request === generation.current) setConnecting(false); }
  }, []);
  useEffect(() => { void connect(); return () => { generation.current += 1; }; }, [connect]);
  return { session, messages, setMessages, connecting, error, setError, generation, connect };
}

export function useWidget() {
  const connection = useWidgetConnection();
  const { session, setMessages, connecting, setError, generation } = connection;
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  async function deliver(message: WidgetMessage) {
    if (!session || locked.current || connecting) return;
    locked.current = true; setBusy(true); setError("");
    const request = generation.current;
    setMessages((rows) => rows.some((row) => row.id === message.id)
      ? rows.map((row) => row.id === message.id ? { ...row, failed: false } : row) : [...rows, message]);
    try {
      const response = await widgetFetch<{ assistant_message: WidgetMessage }>(`/widget/conversations/${session.conversation_id}/messages`, {
        method: "POST", token: session.access_token, body: JSON.stringify({ content: message.content }),
      });
      if (request !== generation.current) return;
      setMessages((rows) => [...rows, response.assistant_message]);
    } catch {
      if (request !== generation.current) return;
      setMessages((rows) => rows.map((row) => row.id === message.id ? { ...row, failed: true } : row));
      setError("未确认收到这条消息，可在消息旁重试。回复可能已生成，重试前可重新连接查看记录。");
    } finally { locked.current = false; if (request === generation.current) setBusy(false); }
  }
  async function sendText(raw: string) {
    const content = raw.trim();
    if (!session || !content || locked.current || connecting) return;
    setText(""); await deliver({ id: crypto.randomUUID(), role: "user", content });
  }
  return { ...connection, text, setText, busy, clearError: () => setError(""),
    ready: Boolean(session) && !connecting, sendText, retry: deliver };
}
