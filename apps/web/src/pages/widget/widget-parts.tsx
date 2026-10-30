import { Button, Input } from "antd";
import { ArrowUpOutlined } from "@ant-design/icons";
import { useState, type FormEvent, type KeyboardEvent } from "react";
import { MarkdownBody } from "../../components/chat/MarkdownBody";
import type { WidgetMessage } from "./widget-service";
import type { useWidget } from "./use-widget";

type WidgetState = ReturnType<typeof useWidget>;
const QUICK_REPLIES = ["退货政策", "发货时效", "如何开发票", "转人工客服"];
const TEXTAREA_ROWS = { minRows: 1, maxRows: 4 };

export function WidgetWelcome({ state }: { state: WidgetState }) {
  return <section className="af-w-welcome"><h2>有什么可以帮您？</h2><p>咨询订单、售后或发票，也可以直接转人工客服。</p>
    <div className="af-w-quick">{QUICK_REPLIES.map((question) => <button key={question} type="button"
      disabled={!state.ready || state.busy} onClick={() => void state.sendText(question)}>{question}</button>)}</div>
  </section>;
}

export function WidgetBubble({ message, state }: { message: WidgetMessage; state: WidgetState }) {
  const user = message.role === "user";
  return <article className={`af-w-row ${user ? "af-w-row--user" : ""}`} aria-label={user ? "您的消息" : message.role === "staff" ? "人工客服回复" : "智能客服回复"}>
    <div className="af-w-message-content">{!user && <span className="af-w-message-author">{message.role === "staff" ? "人工客服" : "智能客服"}</span>}
      <div className={`af-w-bubble ${user ? "af-w-bubble--user" : ""}`}>
        {user ? message.content : <MarkdownBody content={message.content} />}</div>
      {message.failed && <div className="af-w-failed"><span>未确认收到</span><Button type="text" disabled={state.busy || !state.ready}
        onClick={() => void state.retry(message)}>重试发送</Button></div>}
    </div>
  </article>;
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
