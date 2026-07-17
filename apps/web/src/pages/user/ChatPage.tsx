import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  Conversation,
  Message,
  setToken,
  User,
} from "../../api/client";
import { useFeatures } from "../../plugins/features";

export function ChatPage() {
  const nav = useNavigate();
  const { enabled } = useFeatures();
  const [me, setMe] = useState<User | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const user = await api<User>("/api/v1/admin/auth/me");
        setMe(user);
        const list = await api<Conversation[]>("/api/v1/chat/conversations");
        setConversations(list);
        if (list[0]) setActiveId(list[0].id);
      } catch {
        setToken(null);
        nav("/login");
      }
    })();
  }, [nav]);

  useEffect(() => {
    if (!activeId) return;
    (async () => {
      const rows = await api<Message[]>(
        `/api/v1/chat/conversations/${activeId}/messages`,
      );
      setMessages(rows);
    })();
  }, [activeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function newChat() {
    const conv = await api<Conversation>("/api/v1/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title: "新会话" }),
    });
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    setMessages([]);
  }

  async function onSend(e: FormEvent) {
    e.preventDefault();
    if (!activeId || !input.trim() || sending) return;
    setSending(true);
    setError(null);
    const content = input.trim();
    setInput("");
    try {
      const res = await api<{
        user_message: Message;
        assistant_message: Message;
      }>(`/api/v1/chat/conversations/${activeId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setMessages((prev) => [...prev, res.user_message, res.assistant_message]);
      const list = await api<Conversation[]>("/api/v1/chat/conversations");
      setConversations(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败");
      setInput(content);
    } finally {
      setSending(false);
    }
  }

  function logout() {
    setToken(null);
    nav("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-head">
          <span className="brand-mark sm">AF</span>
          <strong>AskFlow</strong>
        </div>
        <button className="primary" onClick={newChat}>
          新建会话
        </button>
        <ul className="conv-list">
          {conversations.map((c) => (
            <li key={c.id}>
              <button
                className={c.id === activeId ? "active" : ""}
                onClick={() => setActiveId(c.id)}
              >
                <span className="title">{c.title}</span>
                <span className="status">{c.status}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="sidebar-foot">
          <span>{me?.username}</span>
          {enabled("ticket") ? (
            <a className="linkish" href="/tickets">
              工单
            </a>
          ) : null}
          <a className="linkish" href="/admin">
            Admin
          </a>
          <button className="linkish" onClick={logout}>
            退出
          </button>
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <h2>智能客服</h2>
          <p>诚实 RAG · 意图路由 · 可转人工</p>
        </header>

        <div className="message-list">
          {messages.length === 0 && (
            <div className="empty-state">
              <h3>有什么可以帮您？</h3>
              <p>试试：退货政策 / 查订单物流 / 转人工客服</p>
            </div>
          )}
          {messages.map((m) => (
            <article key={m.id} className={`bubble ${m.role}`}>
              <div className="bubble-role">{m.role === "user" ? "我" : "助手"}</div>
              <div className="bubble-body">{m.content}</div>
              {m.role === "assistant" && m.meta?.answer_confidence != null && (
                <div className="confidence">
                  置信度 {Number(m.meta.answer_confidence).toFixed(2)}
                  {m.meta.route ? ` · ${String(m.meta.route)}` : ""}
                  {m.meta.refused ? " · 拒答" : ""}
                </div>
              )}
              {m.role === "assistant" && Array.isArray(m.meta?.sources) && (m.meta.sources as { source?: string; text?: string; index?: number }[]).length > 0 && (
                <div className="sources">
                  <div className="sources-title">来源</div>
                  {(m.meta.sources as { source?: string; text?: string; index?: number }[]).map((s, i) => (
                    <div key={i} className="source-item">
                      [{s.index ?? i + 1}] {s.source}: {(s.text || "").slice(0, 120)}
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
          <div ref={bottomRef} />
        </div>

        {error && <div className="error-banner inline">{error}</div>}

        <form className="composer" onSubmit={onSend}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={activeId ? "输入问题，Enter 发送" : "请先新建会话"}
            rows={2}
            disabled={!activeId || sending}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void onSend(e);
              }
            }}
          />
          <button type="submit" disabled={!activeId || sending || !input.trim()}>
            {sending ? "…" : "发送"}
          </button>
        </form>
      </main>
    </div>
  );
}
