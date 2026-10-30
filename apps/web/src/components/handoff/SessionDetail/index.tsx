import { useState } from "react";
import { Button, Descriptions, Drawer, Input } from "antd";
import { StatusBadge, intentLabel } from "../../admin";
import { EmptyState, QueryFeedback } from "../../admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../common/action-feedback";
import { MarkdownBody } from "../../chat/MarkdownBody";
import type { Handoff, Message } from "../../../api/types";
import { useHandoffMessages, useStaffReply } from "../../../hooks/use-ops";
import { useMe } from "../../../hooks/use-auth";
import { formatDateTime } from "../../../utils";

type SessionDetailProps = { open: boolean; session: Handoff | null; onClose: () => void };
const REPLY_ROWS = { minRows: 3, maxRows: 8 };
const ROLE_LABELS: Record<string, string> = { user: "客户", staff: "人工座席", assistant: "智能助手" };

function StaffMessage({ message }: { message: Message }) {
  return <article className={"af-staff-msg af-staff-msg--" + message.role}>
    <div className="af-staff-message-label"><strong>{ROLE_LABELS[message.role] ?? message.role}</strong>
      <span>{formatDateTime(message.created_at, true)}</span></div>
    {message.role === "user" ? <p className="af-record-copy">{message.content}</p> : <MarkdownBody content={message.content} />}
  </article>;
}

function StaffConversation({ session }: { session: Handoff }) {
  const query = useHandoffMessages(session.id);
  const reply = useStaffReply();
  const feedback = useActionFeedback();
  const [text, setText] = useState("");
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

function SessionWorkspace({ session }: { session: Handoff }) {
  const me = useMe();
  const mine = session.status === "claimed" && session.claimed_by === me.data?.id;
  return <div className="af-work-stack"><Descriptions column={1} items={[
    { key: "status", label: "接管状态", children: <StatusBadge value={session.status} /> },
    { key: "customer", label: "客户", children: session.user_name || "访客" },
    { key: "intent", label: "问题意图", children: intentLabel(session.intent || "handoff") },
    { key: "owner", label: "认领座席", children: session.claimed_by_name || session.claimed_by || "尚未认领" },
    { key: "conversation", label: "会话编号", children: <span className="af-record-secondary">{session.conversation_id}</span> },
  ]} /><section><h2 className="af-staff-heading">问题摘要</h2><p className="af-work-preview">{session.summary || "暂未生成摘要。"}</p></section>
    <QueryFeedback query={me} />
    {mine ? <StaffConversation key={session.id} session={session} /> : <EmptyState title={me.isLoading ? "正在确认座席身份…" : "认领座席可以查看消息并回复"}
      description={session.claimed_by ? "这个会话当前由其他座席处理。" : "返回接管队列，先认领这个会话。"} />}
  </div>;
}

export function SessionDetail({ open, session, onClose }: SessionDetailProps) {
  return <Drawer title="接管工作台" open={open} onClose={onClose} size="min(560px, 100vw)" destroyOnHidden>
    {open && session && <SessionWorkspace key={session.id} session={session} />}
  </Drawer>;
}
