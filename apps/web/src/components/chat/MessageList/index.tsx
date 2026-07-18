import type { CitationSource, Message } from "../../../api/types";
import { useSourcePanel } from "../../../stores/ui-store";
import { ConfidenceBadge } from "../ConfidenceBadge";
import { MarkdownBody } from "../MarkdownBody";
import { StaffBubble } from "../StaffBubble";

type MessageListProps = {
  messages: Message[];
  streamingText?: string;
  streaming?: boolean;
  emptyHint?: string;
};

function readSources(meta?: Record<string, unknown>): CitationSource[] {
  if (!meta || !Array.isArray(meta.sources)) return [];
  return meta.sources as CitationSource[];
}

function MessageBubble({ message }: { message: Message }) {
  const openSources = useSourcePanel((s) => s.openSources);
  const role = message.role;
  if (role === "staff") {
    return <StaffBubble content={message.content} />;
  }
  const isUser = role === "user";
  const sources = readSources(message.meta);
  const confidence =
    typeof message.meta?.answer_confidence === "number"
      ? message.meta.answer_confidence
      : null;
  const route =
    typeof message.meta?.route === "string" ? message.meta.route : null;
  const refused = Boolean(message.meta?.refused);

  return (
    <article className={`af-bubble ${isUser ? "af-bubble--user" : "af-bubble--bot"}`}>
      <div className="af-bubble-role">{isUser ? "我" : "助手"}</div>
      {isUser ? (
        <div className="af-bubble-plain">{message.content}</div>
      ) : (
        <MarkdownBody content={message.content} />
      )}
      {!isUser ? (
        <div className="af-bubble-meta">
          <ConfidenceBadge
            confidence={confidence}
            route={route}
            refused={refused}
          />
          {sources.length > 0 ? (
            <button
              type="button"
              className="af-cite-btn"
              onClick={() => openSources(sources, "回答引用")}
            >
              查看引用 · {sources.length}
            </button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

export function MessageList({
  messages,
  streamingText = "",
  streaming = false,
  emptyHint = "试试：退货政策 / 查订单物流 / 转人工客服",
}: MessageListProps) {
  const empty = messages.length === 0 && !streaming;
  if (empty) {
    return (
      <div className="af-chat-empty">
        <div className="af-chat-empty-icon">AF</div>
        <h3>有什么可以帮您？</h3>
        <p>{emptyHint}</p>
      </div>
    );
  }

  return (
    <div className="af-message-list">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      {streaming ? (
        <article className="af-bubble af-bubble--bot af-bubble--streaming">
          <div className="af-bubble-role">助手</div>
          {streamingText ? (
            <MarkdownBody content={streamingText} />
          ) : (
            <div className="af-typing">正在思考…</div>
          )}
        </article>
      ) : null}
    </div>
  );
}
