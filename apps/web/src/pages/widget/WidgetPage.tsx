import { useEffect, useRef } from "react";
import { Alert, Button } from "antd";
import { BrandMark } from "../../components/layout/BrandMark";
import { SourcePanel } from "../../components/chat/SourcePanel";
import { useWidget } from "./use-widget";
import { WidgetBubble, WidgetComposer, WidgetWelcome } from "./widget-parts";

export function WidgetPage() {
  const state = useWidget();
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    bottomRef.current?.scrollIntoView({ behavior: reduced ? "instant" : "smooth", block: "end" });
  }, [state.messages, state.busy]);
  return <div className="af-w-page"><div className="af-w-shell"><header className="af-w-head"><BrandMark />
    <div className="af-w-head-text"><h1>AskFlow 在线客服</h1><span role="status">
      {state.ready ? "已连接，可开始咨询" : state.connecting ? "正在连接客服…" : "连接暂不可用"}</span></div>
    {!state.connecting && !state.ready && <Button type="text" onClick={() => void state.connect()}>重试连接</Button>}
  </header><div className="af-w-messages" role="log" aria-label="客服对话" aria-live="polite" aria-relevant="additions text">
    {!state.messages.length && <WidgetWelcome state={state} />}
    {state.messages.map((message) => <WidgetBubble key={message.id} message={message} state={state} />)}
    {state.busy && <p className="af-w-pending" role="status">正在回复…</p>}<div ref={bottomRef} />
  </div>{state.error && <div className="af-w-error"><Alert type="error" showIcon title={state.error}
    action={<Button loading={state.connecting} disabled={state.busy} onClick={() => void state.connect()}>重新连接</Button>} /></div>}
  <div className="af-w-service-actions"><span>需要继续处理？</span><Button size="small"
    disabled={!state.ready || state.busy} onClick={() => void state.sendText("转人工客服")}>转人工客服</Button></div>
  <WidgetComposer state={state} /><footer className="af-w-foot">AskFlow · 订单与售后支持</footer></div><SourcePanel /></div>;
}
