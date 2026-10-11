import { Avatar } from "antd";
import { CustomerServiceOutlined } from "@ant-design/icons";
import { MarkdownBody } from "../MarkdownBody";

type StaffBubbleProps = {
  content: string;
  agentLabel?: string;
};

export function StaffBubble({
  content,
  agentLabel = "人工客服",
}: StaffBubbleProps) {
  return (
    <div className="af-msg af-msg--staff">
      <Avatar
        size={32}
        className="af-msg-avatar af-msg-avatar--staff"
        icon={<CustomerServiceOutlined />}
      />
      <div className="af-msg-col">
        <div className="af-msg-name">{agentLabel}</div>
        <article className="af-bubble af-bubble--staff">
          <MarkdownBody content={content} />
        </article>
      </div>
    </div>
  );
}
