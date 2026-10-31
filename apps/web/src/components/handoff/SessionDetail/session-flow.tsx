import { useEffect, useState } from "react";
import { Button, Popconfirm } from "antd";
import { CustomerServiceOutlined } from "@ant-design/icons";
import type { Handoff } from "../../../api/types";
import { useClaimHandoff, useReturnHandoff } from "../../../hooks/use-ops";
import { intentLabel } from "../../admin";
import { ActionFeedback, useActionFeedback } from "../../common/action-feedback";
import { handoffActions } from "../actions";
import { HandoffStatus } from "../status";
import { StaffConversation } from "./staff-conversation";
import type { SessionDetailProps } from ".";

type Props = SessionDetailProps & { session: Handoff };

function useSessionActions(props: Props) {
  const claim = useClaimHandoff();
  const ret = useReturnHandoff();
  const feedback = useActionFeedback();
  const [replyBusy, setReplyBusy] = useState(false);
  const busy = feedback.busy || replyBusy;
  useEffect(() => { props.onBusyChange(busy); }, [busy, props.onBusyChange]);
  useEffect(() => () => props.onBusyChange(false), [props.onBusyChange]);
  async function claimSession() { await feedback.run(() => claim.mutateAsync(props.session.id)); }
  async function returnSession() {
    const done = await feedback.run(() => ret.mutateAsync(props.session.id), "已交还智能助手，后续消息将由 AI 接续。");
    if (done) props.onDraftChange("");
  }
  return { feedback, busy, setReplyBusy, claimSession, returnSession };
}

function TransferContext({ session }: { session: Handoff }) {
  return <details className="af-transfer-context" open>
    <summary><span>转接摘要</span><span>{intentLabel(session.intent || "handoff")}</span></summary>
    <p>{session.summary || "暂无自动摘要，请在认领后查看客户的历史消息。"}</p>
    <dl><div><dt>会话编号</dt><dd title={session.conversation_id}>{session.conversation_id}</dd></div>
      <div><dt>认领座席</dt><dd>{session.claimed_by_name || (session.claimed_by ? "其他座席" : "尚未认领")}</dd></div></dl>
  </details>;
}

export function SessionFlow(props: Props) {
  const { session, currentUser } = props;
  const state = useSessionActions(props);
  const can = handoffActions(session, currentUser?.id);
  const readable = can.ret || currentUser?.role === "admin";
  return <>
    <header className="af-service-header"><div><h2>{session.user_name || "访客"}</h2>
      <HandoffStatus status={session.status} /></div>
      {can.ret && <Popconfirm title="交还智能助手？" description="AI 将接续后续对话，未发送的草稿将清除。"
        okText="确认交还" cancelText="继续人工服务" onConfirm={() => state.returnSession()} disabled={state.busy}>
        <Button disabled={state.busy}>交还 AI</Button></Popconfirm>}
    </header>
    <TransferContext session={session} /><ActionFeedback state={state.feedback} />
    {readable ? <StaffConversation session={session} canReply={can.ret} draft={props.draft}
      onDraftChange={props.onDraftChange} onBusyChange={state.setReplyBusy} disabled={state.feedback.busy} /> :
      <div className="af-handoff-empty af-service-locked"><CustomerServiceOutlined />
        <h3>{can.claim ? "准备接续这段对话" : "当前会话由其他座席处理或已结束"}</h3>
        <p>{can.claim ? "认领后即可查看完整历史，并以人工客服身份回复。" : "可在左侧选择待认领会话，或继续您已认领的服务。"}</p></div>}
    {can.claim && <footer className="af-service-claim"><span>先认领，让客户的问题有明确负责人。</span>
      <Button type="primary" loading={state.feedback.busy} disabled={!currentUser}
        onClick={() => void state.claimSession()}>认领并开始回复</Button></footer>}
  </>;
}
