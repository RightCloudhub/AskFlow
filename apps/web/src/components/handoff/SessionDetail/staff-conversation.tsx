import { useEffect, useState } from "react";
import { Button, Input } from "antd";
import { EmptyState, QueryFeedback } from "../../admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../common/action-feedback";
import { MarkdownBody } from "../../chat/MarkdownBody";
import type { Handoff, Message } from "../../../api/types";
import { useHandoffMessages, useStaffReply } from "../../../hooks/use-ops";
import { formatDateTime } from "../../../utils";

const REPLY_ROWS = { minRows: 3, maxRows: 8 };
const ROLE_LABELS: Record<string, string> = { user: "客户", staff: "人工座席", assistant: "智能助手" };

function StaffMessage({ message }: { message: Message }) {
  return <article className={"af-staff-msg af-staff-msg--" + message.role}>
    <div className="af-staff-message-label"><strong>{ROLE_LABELS[message.role] ?? message.role}</strong>
      <span>{formatDateTime(message.created_at, true)}</span></div>
    {message.role === "user" ? <p className="af-record-copy">{message.content}</p> : <MarkdownBody content={message.content} />}
  </article>;
}

export function StaffConversation({ session, onBusyChange }: { session: Handoff; onBusyChange: (busy: boolean) => void }) {
  const query = useHandoffMessages(session.id);
  const reply = useStaffReply();
  const feedback = useActionFeedback();
  const [text, setText] = useState("");
  useEffect(() => { onBusyChange(feedback.busy); }, [feedback.busy, onBusyChange]);
  useEffect(() => () => onBusyChange(false), [onBusyChange]);
  async function send() {
    if (!text.trim()) return;
    const done = await feedback.run(() => reply.mutateAsync({ id: session.id, content: text.trim() }), "回复已发送。");
    if (done) setText("");
  }
  return <section className="af-work-stack"><h2 className="af-staff-heading">会话消息</h2><QueryFeedback query={query} />
    <div className="af-staff-msgs">
      {query.isLoading ? <p className="af-work-help">正在读取历史消息…</p> : query.data?.length ?
        query.data.map((message) => <StaffMessage key={message.id} message={message} />) :
        !query.isError && <EmptyState title="暂无会话消息" description="客户和座席的消息会显示在这里。" />}
    </div>
    <ActionFeedback state={feedback} /><form className="af-work-stack" onSubmit={(event) => { event.preventDefault(); void send(); }}>
      <label className="af-field"><span>以人工座席身份回复</span><Input.TextArea value={text}
        onChange={(event) => { setText(event.target.value); feedback.clear(); }} autoSize={REPLY_ROWS}
        disabled={feedback.busy || query.isError} placeholder="填写给客户的回复" /></label>
      <Button type="primary" htmlType="submit" loading={feedback.busy} disabled={!text.trim() || query.isError}>发送回复</Button>
    </form>
  </section>;
}
