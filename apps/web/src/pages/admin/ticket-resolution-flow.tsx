import { useEffect, useState } from "react";
import { Button, Checkbox } from "antd";
import type { AdminTicket } from "../../api/types";
import { PriorityTag, StatusBadge, ticketTypeLabel } from "../../components/admin";
import { FlowFrame } from "../../components/common/FlowFrame";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useUpdateAdminTicket } from "../../hooks/use-ops";

const TITLES = ["核对工单", "处理与结案", "处理结果"];
type Props = { ticket: AdminTicket; onBusyChange: (busy: boolean) => void; onClose: () => void };

function useResolution({ ticket, onBusyChange }: Props) {
  const [current, setCurrent] = useState(0);
  const [resolved, setResolved] = useState(false);
  const [started, setStarted] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const mutation = useUpdateAdminTicket();
  const feedback = useActionFeedback();
  useEffect(() => { onBusyChange(feedback.busy); }, [feedback.busy, onBusyChange]);
  async function start() {
    if (started || ticket.status === "processing") { setCurrent(1); return; }
    const done = await feedback.run(() => mutation.mutateAsync({ id: ticket.id, status: "processing" }));
    if (done) { setStarted(true); setCurrent(1); }
  }
  async function finish() {
    if (!acknowledged || resolved) return;
    const done = await feedback.run(() => mutation.mutateAsync({ id: ticket.id, status: "resolved" }));
    if (done) { setResolved(true); setCurrent(TITLES.length - 1); }
  }
  function back(index: number) {
    if (feedback.busy || resolved || index >= current) return;
    setCurrent(index); setAcknowledged(false); feedback.clear();
  }
  return { current, resolved, acknowledged, setAcknowledged, feedback, start, finish, back };
}

function TicketSummary({ ticket }: { ticket: AdminTicket }) {
  return <div className="af-form-review"><dl><div><dt>客户问题</dt><dd>{ticket.title}</dd></div>
      <div><dt>工单编号</dt><dd>{ticket.id}</dd></div><div><dt>业务类型</dt><dd>{ticketTypeLabel(ticket.type)}</dd></div>
      <div><dt>负责人</dt><dd>{ticket.assignee || "尚未分配"}</dd></div>
      <div><dt>优先级</dt><dd><PriorityTag value={ticket.priority} /></dd></div></dl></div>;
}

function ResolutionActions({ state }: { state: ReturnType<typeof useResolution> }) {
  return <><p className="af-work-help">{state.current === 0 ? "核对客户问题后开始处理。" : "请先完成实际处理，再将工单标记为已解决。"}</p>
        {state.current === 1 && <Checkbox checked={state.acknowledged} disabled={state.feedback.busy}
          onChange={(event) => state.setAcknowledged(event.target.checked)}>已确认客户问题得到解决</Checkbox>}
        <div className="af-form-flow-actions">
          {state.current > 0 && <Button disabled={state.feedback.busy} onClick={() => state.back(0)}>上一步</Button>}
          <Button type="primary" loading={state.feedback.busy} disabled={state.current === 1 && !state.acknowledged}
            onClick={() => void (state.current === 0 ? state.start() : state.finish())}>
            {state.current === 0 ? "进入处理" : "标记已解决"}</Button>
        </div></>;
}

export function TicketResolutionFlow(props: Props) {
  const state = useResolution(props);
  const { ticket, onClose } = props;
  const ended = ticket.status !== "pending" && ticket.status !== "processing";
  return <FlowFrame titles={TITLES} current={ended ? TITLES.length - 1 : state.current} onBack={state.back}
    busy={state.feedback.busy} backDisabled={ended || state.resolved} focusOnMount>
    <TicketSummary ticket={ticket} />
    {ended || state.resolved ? <div className="af-flow-success"><p role="status">工单已结束处理。</p>
      <StatusBadge value={state.resolved ? "resolved" : ticket.status} /><Button onClick={onClose}>返回工单列表</Button></div> :
      <ResolutionActions state={state} />}
    <ActionFeedback state={state.feedback} />
  </FlowFrame>;
}
