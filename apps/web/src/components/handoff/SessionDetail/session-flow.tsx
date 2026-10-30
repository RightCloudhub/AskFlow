import { useEffect, useState } from "react";
import { Button, Descriptions } from "antd";
import type { Handoff } from "../../../api/types";
import { useClaimHandoff, useReturnHandoff } from "../../../hooks/use-ops";
import { useMe } from "../../../hooks/use-auth";
import { StatusBadge, intentLabel } from "../../admin";
import { QueryFeedback } from "../../admin/workspace";
import { FlowFrame } from "../../common/FlowFrame";
import { ActionFeedback, useActionFeedback } from "../../common/action-feedback";
import { handoffActions } from "../actions";
import { StaffConversation } from "./staff-conversation";

const TITLES = ["核对会话", "人工服务", "核对交还", "交还结果"];
const RETURN_STEP = 2;
type Props = { session: Handoff; onBusyChange: (busy: boolean) => void; onClose: () => void };

function useSessionFlow(props: Props) {
  const [current, setCurrent] = useState(0);
  const [claimed, setClaimed] = useState<Handoff>();
  const [returned, setReturned] = useState(false);
  const [replyBusy, setReplyBusy] = useState(false);
  const me = useMe();
  const claim = useClaimHandoff();
  const ret = useReturnHandoff();
  const feedback = useActionFeedback();
  const session = props.session.status === "queued" && claimed ? claimed : props.session;
  const can = handoffActions(session, me.data?.id);
  const busy = feedback.busy || replyBusy;
  useEffect(() => { props.onBusyChange(busy); }, [busy, props.onBusyChange]);
  async function enter() {
    if (can.ret) { setCurrent(1); return; }
    if (!can.claim || !me.data) return;
    const done = await feedback.run(async () => setClaimed(await claim.mutateAsync(session.id)));
    if (done) setCurrent(1);
  }
  async function returnToAi() {
    if (!can.ret || returned) return;
    const done = await feedback.run(() => ret.mutateAsync(session.id));
    if (done) { setReturned(true); setCurrent(TITLES.length - 1); }
  }
  function back(index: number) {
    if (!busy && !returned && index < current) { setCurrent(index); feedback.clear(); }
  }
  return { current, setCurrent, session, can, busy, me, feedback, returned, enter, returnToAi, back, setReplyBusy };
}

function SessionSummary({ session }: { session: Handoff }) {
  return <div className="af-work-stack"><Descriptions column={1} items={[
    { key: "status", label: "接管状态", children: <StatusBadge value={session.status} /> },
    { key: "customer", label: "客户", children: session.user_name || "访客" },
    { key: "intent", label: "问题意图", children: intentLabel(session.intent || "handoff") },
    { key: "owner", label: "认领座席", children: session.claimed_by_name || session.claimed_by || "尚未认领" },
    { key: "conversation", label: "会话编号", children: session.conversation_id },
  ]} /><p className="af-work-preview">{session.summary || "暂未生成问题摘要。"}</p></div>;
}

type State = ReturnType<typeof useSessionFlow>;

function SessionActions({ state }: { state: State }) {
  if (state.returned) return null;
  if (state.current === 0) return <div className="af-form-flow-actions"><Button type="primary" loading={state.feedback.busy}
    disabled={state.me.isLoading || state.me.isError || (!state.can.claim && !state.can.ret)} onClick={() => void state.enter()}>
    {state.can.ret ? "继续人工服务" : "认领并开始服务"}</Button></div>;
  return <div className="af-form-flow-actions"><Button disabled={state.busy} onClick={() => state.back(state.current - 1)}>上一步</Button>
    {state.current === 1 ? <Button disabled={state.busy || !state.can.ret} onClick={() => state.setCurrent(RETURN_STEP)}>交还智能助手</Button> :
      <Button type="primary" disabled={state.busy || !state.can.ret} loading={state.feedback.busy}
        onClick={() => void state.returnToAi()}>确认交还</Button>}
  </div>;
}

export function SessionFlow(props: Props) {
  const state = useSessionFlow(props);
  return <FlowFrame titles={TITLES} current={state.current} onBack={state.back} busy={state.busy} backDisabled={state.returned} focusOnMount>
    <QueryFeedback query={state.me} />
    {state.current === 0 && <SessionSummary session={state.session} />}
    {state.can.ret && !state.returned && <div hidden={state.current !== 1}>
      <StaffConversation session={state.session} onBusyChange={state.setReplyBusy} /></div>}
    {state.current === RETURN_STEP && <div className="af-work-stack"><SessionSummary session={state.session} />
      <p className="af-work-help">交还后由智能助手继续服务，您将不再以认领座席身份回复。尚未发送的草稿会清除。</p></div>}
    {!state.can.claim && !state.can.ret && !state.returned && <p className="af-work-help">当前会话无法由您认领或回复，请核对接管状态与认领座席。</p>}
    {state.returned && <div className="af-flow-success"><p role="status">会话已交还智能助手。</p><Button onClick={props.onClose}>返回接管队列</Button></div>}
    <ActionFeedback state={state.feedback} /><SessionActions state={state} />
  </FlowFrame>;
}
