import { Button } from "antd";
import { CustomerServiceOutlined } from "@ant-design/icons";
import { Composer, SourcePanel } from "../../components/chat";
import { ConsultationRail } from "../../components/chat/ConsultationRail";
import { AppShell } from "../../components/layout/AppShell";
import { useChatPage } from "../../hooks/use-chat-page";
import { useFeatures } from "../../plugins/features";
import { ChatBody, ChatLoading, type ChatState } from "./chat-parts";

function HumanAction({ state, handoff, closed }: { state: ChatState; handoff: boolean; closed: boolean }) {
  const { enabled } = useFeatures();
  if (!enabled("handoff")) return null;
  return <Button icon={<CustomerServiceOutlined />}
    disabled={handoff || closed || state.streaming || state.creating} onClick={() => void state.suggest("转人工客服")}>
    {handoff ? "人工处理中" : "转人工客服"}</Button>;
}

export function ChatPage() {
  const state = useChatPage();
  const handoff = state.active?.status === "transferred" || Boolean(state.handoffHint);
  const closed = state.active?.status === "closed";
  if (state.loading) return <ChatLoading label="加载会话…" />;
  return <AppShell me={state.meQ.data} conversations={state.convQ.data ?? []}
    activeId={state.activeId} onSelectConversation={state.select}
    onNewChat={() => { void state.create(); }} creating={state.creating}
    title={state.active?.title || "客服工作台"} headerExtra={<HumanAction state={state} handoff={handoff} closed={closed} />}
    subtitle={handoff ? "已有对话将由人工客服继续处理" : "咨询、依据与处理进度，都在这里"}>
    <div className="af-chat-workspace"><div className="af-chat-conversation"><ChatBody state={state} />
      <Composer disabled={closed || state.creating} sending={state.streaming}
        placeholder={closed ? "会话已结束，请新建会话继续咨询" : "描述您的问题，或提供订单号…"}
        onSend={(text) => state.suggest(text)} />
    </div><ConsultationRail messages={state.msgQ.data ?? []} status={state.active?.status} handoff={handoff} /></div>
    <SourcePanel />
  </AppShell>;
}
