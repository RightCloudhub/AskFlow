import { Avatar } from "antd";
import { FileTextOutlined, UserOutlined } from "@ant-design/icons";
import type { CitationSource, Message } from "../../../api/types";
import { useSourcePanel } from "../../../stores/ui-store";
import { BrandMark } from "../../layout/BrandMark";
import { ConfidenceBadge } from "../ConfidenceBadge";
import { MarkdownBody } from "../MarkdownBody";
import { StaffBubble } from "../StaffBubble";
import { parseApiDate } from "../../../utils";

const AVATAR_SIZE = 32;

function formatTime(iso?: string) {
  const date = parseApiDate(iso);
  return date?.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) ?? "";
}

export function BotAvatar() {
  return <Avatar size={AVATAR_SIZE} className="af-msg-avatar af-msg-avatar--bot" icon={<BrandMark />} />;
}

function UserBubble({ message }: { message: Message }) {
  const time = formatTime(message.created_at);
  return <div className="af-msg af-msg--user"><div className="af-msg-col">
    {time && <div className="af-msg-name">{time}</div>}
    <article className="af-bubble af-bubble--user"><div className="af-bubble-plain">{message.content}</div></article>
  </div><Avatar size={AVATAR_SIZE} className="af-msg-avatar af-msg-avatar--user" icon={<UserOutlined />} /></div>;
}

function AssistantBubble({ message }: { message: Message }) {
  const openSources = useSourcePanel((state) => state.openSources);
  const sources = Array.isArray(message.meta?.sources) ? message.meta.sources as CitationSource[] : [];
  const confidence = typeof message.meta?.answer_confidence === "number" ? message.meta.answer_confidence : null;
  const route = typeof message.meta?.route === "string" ? message.meta.route : null;
  const time = formatTime(message.created_at);
  return <div className="af-msg af-msg--bot"><BotAvatar /><div className="af-msg-col">
    <div className="af-msg-name">智能助手{time && <span className="af-msg-time">{time}</span>}</div>
    <article className="af-bubble af-bubble--bot"><MarkdownBody content={message.content} /></article>
    <div className="af-bubble-meta"><ConfidenceBadge confidence={confidence} route={route} refused={Boolean(message.meta?.refused)} />
      {sources.length > 0 && <button type="button" className="af-cite-btn" onClick={() => openSources(sources, "回答引用")}>
        <FileTextOutlined /> {sources.length} 条引用
      </button>}
    </div>
  </div></div>;
}

export function MessageBubble({ message }: { message: Message }) {
  if (message.role === "staff") return <StaffBubble content={message.content} />;
  return message.role === "user" ? <UserBubble message={message} /> : <AssistantBubble message={message} />;
}
