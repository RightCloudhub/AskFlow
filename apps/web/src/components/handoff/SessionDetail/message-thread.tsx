import { useEffect, useRef, useState } from "react";
import { Button, Skeleton } from "antd";
import { ArrowDownOutlined } from "@ant-design/icons";
import { MarkdownBody } from "../../chat/MarkdownBody";
import type { Message } from "../../../api/types";
import { formatDateTime } from "../../../utils";

const ROLE_LABELS: Record<string, string> = { user: "客户", staff: "人工客服", assistant: "智能助手" };
const BOTTOM_THRESHOLD_PX = 80;
const PLACEHOLDER_ROWS = 3;

function StaffMessage({ message }: { message: Message }) {
  return <article className={`af-service-message af-service-message--${message.role}`}>
    <div className="af-service-message-meta"><strong>{ROLE_LABELS[message.role] ?? message.role}</strong>
      <time>{formatDateTime(message.created_at, true)}</time></div>
    <div className="af-service-message-body">{message.role === "user" ?
      <p>{message.content}</p> : <MarkdownBody content={message.content} />}</div>
  </article>;
}

export function MessageThread({ messages, loading }: { messages?: Message[]; loading: boolean }) {
  const container = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);
  const [unseen, setUnseen] = useState(false);
  const latest = messages?.[messages.length - 1]?.id;
  function scrollDown() {
    const node = container.current;
    if (node) node.scrollTop = node.scrollHeight;
    atBottom.current = true;
    setUnseen(false);
  }
  useEffect(() => {
    if (atBottom.current) scrollDown();
    else setUnseen(true);
  }, [latest]);
  return <div className="af-thread-wrap"><div className="af-service-thread" ref={container}
    role="log" tabIndex={0} aria-label="客户与客服对话" aria-live="polite" aria-relevant="additions" onScroll={() => {
      const node = container.current;
      if (!node) return;
      atBottom.current = node.scrollHeight - node.scrollTop - node.clientHeight < BOTTOM_THRESHOLD_PX;
      if (atBottom.current) setUnseen(false);
    }}>
    {loading ? <Skeleton active={false} paragraph={{ rows: PLACEHOLDER_ROWS }} /> :
      messages?.length ? messages.map((message) => <StaffMessage key={message.id} message={message} />) :
        <p className="af-thread-empty">暂无会话消息。</p>}
  </div>{unseen && <Button className="af-thread-new" icon={<ArrowDownOutlined />} onClick={scrollDown}>查看新消息</Button>}</div>;
}
