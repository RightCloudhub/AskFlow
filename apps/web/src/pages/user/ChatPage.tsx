import { Composer, SourcePanel } from "../../components/chat";
import { AppShell } from "../../components/layout/AppShell";
import { useChatPage } from "../../hooks/use-chat-page";
import { ChatBody, ChatLoading } from "./chat-parts";

export function ChatPage() {
  const state = useChatPage();
  const handoff = state.active?.status === "transferred" || Boolean(state.handoffHint);
  if (state.loading) return <ChatLoading label="加载会话…" />;
  return <AppShell me={state.meQ.data} conversations={state.convQ.data ?? []}
    activeId={state.activeId} onSelectConversation={state.select}
    onNewChat={() => { void state.create(); }} creating={state.creating}
    title={state.active?.title || "智能客服"}
    subtitle={handoff ? "已转接人工客服，座席认领后将继续为您服务" : "基于企业知识库作答，可随时转人工"}>
    <ChatBody state={state} />
    <Composer disabled={!state.activeId} sending={state.streaming}
      placeholder={state.activeId ? undefined : "请先新建会话，或点击上方的常见问题"}
      onSend={(text) => state.send(text, state.activeId)} />
    <SourcePanel />
  </AppShell>;
}
