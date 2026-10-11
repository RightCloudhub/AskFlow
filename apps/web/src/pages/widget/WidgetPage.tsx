import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { Alert, Avatar, Button, Input } from "antd";
import {
  ArrowUpOutlined,
  CustomerServiceOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { MarkdownBody } from "../../components/chat/MarkdownBody";

const API = "/api/v1";
const STORAGE_KEY = "askflow_widget_session";
const QUICK_REPLIES = ["退货政策", "发货时效", "如何开发票", "转人工客服"];

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

function WidgetBubble({ msg }: { msg: Msg }) {
  const isUser = msg.role === "user";
  const isStaff = msg.role === "staff";
  if (isUser) {
    return (
      <div className="af-w-row af-w-row--user">
        <div className="af-w-bubble af-w-bubble--user">{msg.content}</div>
      </div>
    );
  }
  return (
    <div className="af-w-row">
      <Avatar
        size={28}
        className={`af-w-avatar ${isStaff ? "af-w-avatar--staff" : ""}`}
        icon={isStaff ? <CustomerServiceOutlined /> : <RobotOutlined />}
      />
      <div className={`af-w-bubble ${isStaff ? "af-w-bubble--staff" : ""}`}>
        <MarkdownBody content={msg.content} />
      </div>
    </div>
  );
}

export function WidgetPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [composing, setComposing] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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
        const hist = await widgetFetch<
          Array<{ role: string; content: string }>
        >(`/widget/conversations/${s.conversation_id}/messages`, {
          token: s.access_token,
        });
        setMessages(hist.map((m) => ({ role: m.role, content: m.content })));
      } catch {
        sessionStorage.removeItem(STORAGE_KEY);
        setError("客服暂时无法连接，请稍后刷新重试");
      }
    })();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function sendText(raw: string) {
    const content = raw.trim();
    if (!session || !content || busy) return;
    setBusy(true);
    setError("");
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
      setMessages((m) => [
        ...m,
        { role: "assistant", content: r.assistant_message.content },
      ]);
    } catch {
      setError("消息发送失败，请稍后重试");
    } finally {
      setBusy(false);
    }
  }

  function send(e: FormEvent) {
    e.preventDefault();
    void sendText(text);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      e.key === "Enter" &&
      !e.shiftKey &&
      !composing &&
      !e.nativeEvent.isComposing
    ) {
      e.preventDefault();
      void sendText(text);
    }
  }

  const ready = Boolean(session);

  return (
    <div className="af-w-page">
      <div className="af-w-shell">
        <header className="af-w-head">
          <Avatar
            size={36}
            className="af-w-head-avatar"
            icon={<RobotOutlined />}
          />
          <div className="af-w-head-text">
            <strong>AskFlow 在线客服</strong>
            <span>
              <i className={`af-w-dot ${ready ? "on" : ""}`} />
              {ready ? "在线 · 通常几秒内回复" : "正在连接…"}
            </span>
          </div>
        </header>

        <div className="af-w-messages">
          <div className="af-w-row">
            <Avatar
              size={28}
              className="af-w-avatar"
              icon={<RobotOutlined />}
            />
            <div className="af-w-bubble">
              您好，我是智能客服助手。可以咨询售后政策、订单与发票等问题，也可以随时转人工。
            </div>
          </div>
          {!messages.length ? (
            <div className="af-w-quick">
              {QUICK_REPLIES.map((q) => (
                <button
                  key={q}
                  type="button"
                  disabled={!ready || busy}
                  onClick={() => void sendText(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          ) : null}
          {messages.map((m, i) => (
            <WidgetBubble key={`${m.role}-${i}`} msg={m} />
          ))}
          {busy ? (
            <div className="af-w-row">
              <Avatar
                size={28}
                className="af-w-avatar"
                icon={<RobotOutlined />}
              />
              <div className="af-w-bubble">
                <div className="af-typing" aria-label="正在输入">
                  <i />
                  <i />
                  <i />
                </div>
              </div>
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>

        {error ? (
          <div className="af-w-error">
            <Alert
              type="error"
              showIcon
              title={error}
              closable
              onClose={() => setError("")}
            />
          </div>
        ) : null}

        <form className="af-w-form" onSubmit={send}>
          <Input.TextArea
            value={text}
            onChange={(ev) => setText(ev.target.value)}
            onKeyDown={onKeyDown}
            onCompositionStart={() => setComposing(true)}
            onCompositionEnd={() => setComposing(false)}
            placeholder="输入您的问题…"
            disabled={!ready}
            variant="borderless"
            autoSize={{ minRows: 1, maxRows: 4 }}
          />
          <Button
            type="primary"
            shape="circle"
            htmlType="submit"
            icon={<ArrowUpOutlined />}
            loading={busy}
            disabled={!ready || busy || !text.trim()}
            aria-label="发送"
          />
        </form>
        <div className="af-w-foot">由 AskFlow 提供技术支持</div>
      </div>
    </div>
  );
}
