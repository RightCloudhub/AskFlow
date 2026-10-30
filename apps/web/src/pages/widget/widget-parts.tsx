import { Button, Input } from "antd";
import { ArrowUpOutlined } from "@ant-design/icons";
import { useState, type FormEvent, type KeyboardEvent } from "react";
import { MarkdownBody } from "../../components/chat/MarkdownBody";
import { CitationTag } from "../../components/chat/CitationText";
import { ConfidenceBadge } from "../../components/chat/ConfidenceBadge";
import type { CitationSource } from "../../api/types";
import type { WidgetMessage } from "./widget-service";
import type { useWidget } from "./use-widget";

type WidgetState = ReturnType<typeof useWidget>;
const QUICK_REPLIES = ["退货政策", "发货时效", "如何开发票", "订单查询"];
const TEXTAREA_ROWS = { minRows: 1, maxRows: 4 };
const MESSAGE_ROLES: Record<string, { name: string; aria: string; rowClass: string; bubbleClass: string }> = {
  user: { name: "", aria: "您的消息", rowClass: "af-w-row--user", bubbleClass: "af-w-bubble--user" },
  staff: { name: "人工客服", aria: "人工客服回复", rowClass: "", bubbleClass: "af-w-bubble--staff" },
  assistant: { name: "智能客服", aria: "智能客服回复", rowClass: "", bubbleClass: "" },
};

export function WidgetWelcome({ state }: { state: WidgetState }) {
  return <section className="af-w-welcome"><h2>有什么可以帮您？</h2><p>咨询订单、售后或发票，也可以直接转人工客服。</p>
    <div className="af-w-quick">{QUICK_REPLIES.map((question) => <button key={question} type="button"
      disabled={!state.ready || state.busy} onClick={() => void state.sendText(question)}>{question}</button>)}</div>
  </section>;
}

export function WidgetBubble({ message, state }: { message: WidgetMessage; state: WidgetState }) {
  const user = message.role === "user";
  const role = MESSAGE_ROLES[message.role] ?? MESSAGE_ROLES.assistant;
  const sources = Array.isArray(message.meta?.sources) ? message.meta.sources as CitationSource[] : [];
  return <article className={`af-w-row ${role.rowClass}`} aria-label={role.aria}>
    <div className="af-w-message-content">{role.name && <span className="af-w-message-author">{role.name}</span>}
      <div className={`af-w-bubble ${role.bubbleClass}`}>
        {user ? message.content : <MarkdownBody content={message.content} sources={sources} />}</div>
      {!user && <WidgetEvidence message={message} sources={sources} />}
      {message.failed && <div className="af-w-failed"><span>未确认收到</span><Button type="text" disabled={state.busy || !state.ready}
        onClick={() => void state.retry(message)}>重试发送</Button></div>}
    </div>
  </article>;
}

function WidgetEvidence({ message, sources }: { message: WidgetMessage; sources: CitationSource[] }) {
  const confidence = typeof message.meta?.answer_confidence === "number" ? message.meta.answer_confidence : null;
  const route = typeof message.meta?.route === "string" ? message.meta.route : null;
  return <div className="af-w-evidence">
    {sources.length > 0 && <div className="af-answer-citations"><span>回答依据</span>
      {sources.map((source, index) => <CitationTag key={`${source.source}-${index}`} source={source}
        index={source.index ?? index + 1} sources={sources} />)}</div>}
    <ConfidenceBadge confidence={confidence} route={route} refused={Boolean(message.meta?.refused)} />
  </div>;
}

export function WidgetComposer({ state }: { state: WidgetState }) {
  const [composing, setComposing] = useState(false);
  function submit(event: FormEvent) { event.preventDefault(); void state.sendText(state.text); }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || composing || event.nativeEvent.isComposing) return;
    event.preventDefault(); void state.sendText(state.text);
  }
  return <div className="af-w-composer"><form className="af-w-form" onSubmit={submit}>
    <Input.TextArea value={state.text} onChange={(event) => state.setText(event.target.value)} onKeyDown={keyDown}
      onCompositionStart={() => setComposing(true)} onCompositionEnd={() => setComposing(false)}
      placeholder={state.ready ? "输入您的问题…" : "连接后即可发送问题"} disabled={!state.ready}
      variant="borderless" autoSize={TEXTAREA_ROWS} aria-label="输入客服问题" aria-describedby="af-w-input-hint" />
    <Button type="primary" shape="circle" htmlType="submit" icon={<ArrowUpOutlined />} loading={state.busy}
      disabled={!state.ready || state.busy || !state.text.trim()} aria-label="发送消息" />
  </form><p id="af-w-input-hint" className="af-w-input-hint">Enter 发送 · Shift + Enter 换行</p></div>;
}
