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
    <article className="af-bubble af-bubble--staff">
      <div className="af-bubble-role">{agentLabel}</div>
      <MarkdownBody content={content} />
    </article>
  );
}
