import { Form, Input } from "antd";
import { ActionFeedback, useActionFeedback } from "../../common/action-feedback";
import { GuidedForm } from "../../common/GuidedForm";

const TITLE_MAX = 80;
const DESCRIPTION_ROWS = { minRows: 4, maxRows: 8 };
type TicketFormProps = { loading?: boolean; onSubmit: (payload: { title: string; description: string }) => void | Promise<void> };

export function TicketForm({ loading, onSubmit }: TicketFormProps) {
  const [form] = Form.useForm();
  const feedback = useActionFeedback();
  async function submit(values: Record<string, unknown>) {
    return feedback.run(async () => {
      await onSubmit({ title: String(values.title).trim(), description: String(values.description ?? "").trim() });
    }, "工单已提交，客服会在工单中继续跟进。");
  }
  return <GuidedForm form={form} submitLabel="提交工单" onFinish={submit} disabled={loading} resetOnSuccess
    onValuesChange={feedback.clear} feedback={<ActionFeedback state={feedback} />} steps={[
      { title: "问题概况", fields: ["title"], content: <Form.Item name="title" label="问题标题"
        rules={[{ required: true, whitespace: true, message: "请填写问题标题。" }]}>
        <Input placeholder="例如：收到的商品有破损" maxLength={TITLE_MAX} showCount />
      </Form.Item> },
      { title: "补充详情", fields: ["description"], content: <Form.Item name="description" label="详细描述">
        <Input.TextArea placeholder="请描述问题经过、订单号等信息，便于客服快速处理" autoSize={DESCRIPTION_ROWS} />
      </Form.Item> },
    ]} review={(values) => <dl><div><dt>问题标题</dt><dd>{String(values.title)}</dd></div>
      <div><dt>详细描述</dt><dd>{String(values.description || "未补充")}</dd></div></dl>} />;
}
