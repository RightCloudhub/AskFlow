import { FormEvent, useEffect, useState } from "react";

const API = "/api/v1";
const STORAGE_KEY = "askflow_widget_session";

type Session = {
  access_token: string;
  conversation_id: string;
  visitor_key: string;
};

type Msg = { role: string; content: string };

async function widgetFetch<T>(
  path: string,
  opts: RequestInit & { token?: string } = {},
): Promise<T> {
  const headers = new Headers(opts.headers);
  headers.set("Content-Type", "application/json");
  if (opts.token) headers.set("Authorization", `Bearer ${opts.token}`);
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

function loadStored(): Session | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function WidgetPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        let s = loadStored();
        if (!s) {
          s = await widgetFetch<Session>("/widget/session", {
            method: "POST",
            body: JSON.stringify({
              title: "官网咨询",
              origin: window.location.origin,
            }),
          });
          sessionStorage.setItem(STORAGE_KEY, JSON.stringify(s));
        }
        setSession(s);
        const hist = await widgetFetch<Array<{ role: string; content: string }>>(
          `/widget/conversations/${s.conversation_id}/messages`,
          { token: s.access_token },
        );
        setMessages(hist.map((m) => ({ role: m.role, content: m.content })));
      } catch (e) {
        setError(e instanceof Error ? e.message : "session failed");
      }
    })();
  }, []);

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!session || !text.trim() || busy) return;
    setBusy(true);
    setError("");
    const content = text.trim();
    setText("");
    setMessages((m) => [...m, { role: "user", content }]);
    try {
      const r = await widgetFetch<{
        assistant_message: { content: string };
      }>(`/widget/conversations/${session.conversation_id}/messages`, {
        method: "POST",
        token: session.access_token,
        body: JSON.stringify({ content }),
      });
      setMessages((m) => [...m, { role: "assistant", content: r.assistant_message.content }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "send failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="widget-shell">
      <header className="widget-head">
        <strong>AskFlow 在线客服</strong>
        <span className="meta">访客通道</span>
      </header>
      <div className="widget-messages">
        {messages.map((m, i) => (
          <div key={`${m.role}-${i}`} className={`bubble ${m.role}`}>
            {m.content}
          </div>
        ))}
        {!messages.length ? <p className="meta">有什么可以帮您？</p> : null}
      </div>
      {error ? <p className="error">{error}</p> : null}
      <form className="widget-form" onSubmit={(e) => void send(e)}>
        <input
          value={text}
          onChange={(ev) => setText(ev.target.value)}
          placeholder="输入问题…"
          disabled={!session || busy}
        />
        <button type="submit" disabled={!session || busy || !text.trim()}>
          发送
        </button>
      </form>
    </div>
  );
}
