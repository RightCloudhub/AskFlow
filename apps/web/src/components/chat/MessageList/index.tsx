import { Avatar } from "antd";
import {
  FileTextOutlined,
  SearchOutlined,
  CustomerServiceOutlined,
  RobotOutlined,
  UserOutlined,
} from "@ant-design/icons";
import type { CitationSource, Message } from "../../../api/types";
import { useSourcePanel } from "../../../stores/ui-store";
import { ConfidenceBadge } from "../ConfidenceBadge";
import { MarkdownBody } from "../MarkdownBody";
import { StaffBubble } from "../StaffBubble";
import { parseApiDate } from "../../../utils";

type MessageListProps = {
  messages: Message[];
  streamingText?: string;
  streaming?: boolean;
  emptyHint?: string;
  /** Quick prompts shown on an empty conversation. */
  suggestions?: string[];
  onSuggest?: (text: string) => void;
};

export const DEFAULT_SUGGESTIONS = [
  "退货政策是什么？",
  "帮我查一下订单物流",
  "发票怎么开？",
  "转人工客服",
];

const SUGGESTION_ICONS = [
  <FileTextOutlined key="a" />,
  <SearchOutlined key="b" />,
  <FileTextOutlined key="c" />,
  <CustomerServiceOutlined key="d" />,
];

function readSources(meta?: Record<string, unknown>): CitationSource[] {
  if (!meta || !Array.isArray(meta.sources)) return [];
  return meta.sources as CitationSource[];
}

function formatTime(iso?: string): string {
  const d = parseApiDate(iso);
  if (!d) return "";
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function BotAvatar() {
  return (
    <Avatar
      size={32}
      className="af-msg-avatar af-msg-avatar--bot"
      icon={<RobotOutlined />}
    />
  );
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
  const time = formatTime(message.created_at);

  if (isUser) {
    return (
      <div className="af-msg af-msg--user">
        <div className="af-msg-col">
          {time ? <div className="af-msg-name">{time}</div> : null}
          <article className="af-bubble af-bubble--user">
            <div className="af-bubble-plain">{message.content}</div>
          </article>
        </div>
        <Avatar
          size={32}
          className="af-msg-avatar af-msg-avatar--user"
          icon={<UserOutlined />}
        />
      </div>
    );
  }

  return (
    <div className="af-msg af-msg--bot">
      <BotAvatar />
      <div className="af-msg-col">
        <div className="af-msg-name">
          智能助手{time ? <span className="af-msg-time">{time}</span> : null}
        </div>
        <article className="af-bubble af-bubble--bot">
          <MarkdownBody content={message.content} />
        </article>
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
              <FileTextOutlined /> {sources.length} 条引用
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function MessageList({
  messages,
  streamingText = "",
  streaming = false,
  emptyHint = "我可以解答售后政策、查询订单进度，也能帮您转接人工客服。",
  suggestions = DEFAULT_SUGGESTIONS,
  onSuggest,
}: MessageListProps) {
  const empty = messages.length === 0 && !streaming;
  if (empty) {
    return (
      <div className="af-chat-empty">
        <div className="af-chat-empty-icon">AF</div>
        <h3>您好，有什么可以帮您？</h3>
        <p>{emptyHint}</p>
        {onSuggest && suggestions.length > 0 ? (
          <div className="af-suggest-grid">
            {suggestions.map((s, i) => (
              <button
                key={s}
                type="button"
                className="af-suggest"
                onClick={() => onSuggest(s)}
              >
                <span className="af-suggest-icon">
                  {SUGGESTION_ICONS[i % SUGGESTION_ICONS.length]}
                </span>
                {s}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="af-message-list">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      {streaming ? (
        <div className="af-msg af-msg--bot">
          <BotAvatar />
          <div className="af-msg-col">
            <div className="af-msg-name">智能助手</div>
            <article className="af-bubble af-bubble--bot af-bubble--streaming">
              {streamingText ? (
                <MarkdownBody content={streamingText} />
              ) : (
                <div className="af-typing" aria-label="正在思考">
                  <i />
                  <i />
                  <i />
                </div>
              )}
            </article>
          </div>
        </div>
      ) : null}
    </div>
  );
}
