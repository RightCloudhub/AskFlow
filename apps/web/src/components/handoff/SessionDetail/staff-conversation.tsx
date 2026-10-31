import { useEffect } from "react";
import { Button, Input } from "antd";
import { SendOutlined } from "@ant-design/icons";
import { QueryFeedback } from "../../admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../common/action-feedback";
import type { Handoff } from "../../../api/types";
import { useHandoffMessages, useStaffReply } from "../../../hooks/use-ops";
import { MessageThread } from "./message-thread";

const REPLY_ROWS = { minRows: 3, maxRows: 6 };
type Props = {
  session: Handoff; canReply: boolean; disabled: boolean; draft: string;
  onDraftChange: (text: string) => void; onBusyChange: (busy: boolean) => void;
};

export function StaffConversation(props: Props) {
  const query = useHandoffMessages(props.session.id);
  const reply = useStaffReply();
  const feedback = useActionFeedback();
  const disabled = props.disabled || feedback.busy || query.isError;
  useEffect(() => { props.onBusyChange(feedback.busy); }, [feedback.busy, props.onBusyChange]);
  useEffect(() => () => props.onBusyChange(false), [props.onBusyChange]);
  async function send() {
    if (!props.draft.trim() || disabled || !props.canReply) return;
    const done = await feedback.run(() => reply.mutateAsync({ id: props.session.id, content: props.draft.trim() }), "回复已发送");
    if (done) props.onDraftChange("");
  }
  return <div className="af-service-conversation">
    <div className="af-thread-heading"><h3>对话记录</h3><span role="status">{query.isError ? "同步中断，可重试" : "消息自动同步"}</span></div>
    <QueryFeedback query={query} />
    <MessageThread messages={query.data} loading={query.isLoading} />
    {props.canReply && <form className="af-reply-composer" onSubmit={(event) => { event.preventDefault(); void send(); }}>
      <ActionFeedback state={feedback} />
      <label htmlFor="staff-reply">回复客户</label>
      <Input.TextArea id="staff-reply" value={props.draft} autoSize={REPLY_ROWS}
        disabled={disabled} placeholder="接续客户的问题，输入您的回复…"
        onChange={(event) => { props.onDraftChange(event.target.value); feedback.clear(); }}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) {
            event.preventDefault(); void send();
          }
        }} />
      <div className="af-reply-actions"><span>人工客服身份 · Ctrl / ⌘ + Enter 发送</span>
        <Button type="primary" htmlType="submit" icon={<SendOutlined />} loading={feedback.busy}
          disabled={disabled || !props.draft.trim()}>发送回复</Button></div>
    </form>}
  </div>;
}
