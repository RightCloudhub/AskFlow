import { useState, type FormEvent } from "react";
import { Button, Input } from "antd";
import { SendOutlined } from "@ant-design/icons";
import { ActionFeedback, useActionFeedback } from "../../common/action-feedback";

const TITLE_MAX = 80;
const DESCRIPTION_ROWS = { minRows: 4, maxRows: 8 };
type TicketFormProps = { loading?: boolean; onSubmit: (payload: { title: string; description: string }) => void | Promise<void> };

export function TicketForm({ loading, onSubmit }: TicketFormProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const feedback = useActionFeedback();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || loading) return;
    const saved = await feedback.run(async () => {
      await onSubmit({ title: title.trim(), description: description.trim() });
    }, "工单已提交，客服会在工单中继续跟进。");
    if (saved) { setTitle(""); setDescription(""); }
  }
  return <form className="af-ticket-form" onSubmit={(event) => void submit(event)}>
    <label className="af-field"><span>问题标题</span><Input placeholder="例如：收到的商品有破损" value={title}
      onChange={(event) => { setTitle(event.target.value); feedback.clear(); }} maxLength={TITLE_MAX} showCount required
      disabled={loading || feedback.busy} /></label>
    <label className="af-field"><span>详细描述</span><Input.TextArea placeholder="请描述问题经过、订单号等信息，便于客服快速处理"
      value={description} onChange={(event) => { setDescription(event.target.value); feedback.clear(); }}
      autoSize={DESCRIPTION_ROWS} disabled={loading || feedback.busy} /></label>
    <Button type="primary" htmlType="submit" icon={<SendOutlined />} loading={loading || feedback.busy}
      disabled={!title.trim()} block>提交工单</Button><ActionFeedback state={feedback} />
  </form>;
}
