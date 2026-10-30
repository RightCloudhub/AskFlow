import { useEffect, useRef } from "react";
import { Alert, Spin } from "antd";
import { HandoffBanner, MessageList } from "../../components/chat";
import type { useChatPage } from "../../hooks/use-chat-page";

export type ChatState = ReturnType<typeof useChatPage>;
const LOADING_WIDTH = 120;
const LOADING_HEIGHT = 60;

export function ChatLoading({ label }: { label: string }) {
  return <div className="af-query-state"><Spin description={label}>
    <div style={{ width: LOADING_WIDTH, height: LOADING_HEIGHT }} /></Spin></div>;
}

export function ChatBody({ state }: { state: ChatState }) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); },
    [state.msgQ.data, state.streamText, state.streaming]);
  const staff = Boolean(state.meQ.data?.role && state.meQ.data.role !== "user");
  return <><div className="af-chat-stage">
    {state.handoffHint && <div className="af-chat-banner"><HandoffBanner summary={state.handoffHint}
      onGoAdmin={staff ? () => state.nav("/admin/handoffs") : undefined} /></div>}
    {state.msgQ.isLoading && state.activeId && !state.streaming ? <ChatLoading label="加载消息…" /> :
      <MessageList messages={state.msgQ.data ?? []} streaming={state.streaming}
        streamingText={state.streamText} onSuggest={(text) => { void state.suggest(text); }} />}
    <div ref={bottom} /></div>
    {state.sendError && <div className="af-chat-error"><Alert type="error" showIcon closable
      onClose={() => state.setSendError(null)} title="消息发送失败" description={state.sendError} /></div>}
  </>;
}
