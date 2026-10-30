import type { Message } from "../../../api/types";
import { MarkdownBody } from "../MarkdownBody";
import { BotAvatar, MessageBubble } from "./MessageBubble";
import { ChatEmpty } from "./ChatEmpty";

type MessageListProps = {
  messages: Message[]; streamingText?: string; streaming?: boolean; emptyHint?: string;
  suggestions?: string[]; onSuggest?: (text: string) => void;
};
export const DEFAULT_SUGGESTIONS = ["退货政策是什么？", "帮我查一下订单物流", "发票怎么开？", "转人工客服"];

export function MessageList({
  messages, streamingText = "", streaming = false,
  emptyHint = "我可以解答售后政策、查询订单进度，也能帮您转接人工客服。",
  suggestions = DEFAULT_SUGGESTIONS, onSuggest,
}: MessageListProps) {
  if (messages.length === 0 && !streaming) return <ChatEmpty hint={emptyHint} suggestions={suggestions} onSuggest={onSuggest} />;
  return <div className="af-message-list">
    {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
    {streaming && <div className="af-msg af-msg--bot"><BotAvatar /><div className="af-msg-col">
      <div className="af-msg-name">智能助手</div>
      <article className="af-bubble af-bubble--bot af-bubble--streaming">
        {streamingText ? <MarkdownBody content={streamingText} /> :
          <div className="af-typing" aria-label="正在思考"><i /><i /><i /></div>}
      </article>
    </div></div>}
  </div>;
}
