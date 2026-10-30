import { Form, Input } from "antd";
import { WorkspacePanel } from "../../components/admin/workspace";
import { GuidedForm } from "../../components/common/GuidedForm";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useCreateDraft } from "../../hooks/use-knowledge";

const TITLE_LIMIT = 120;
const EDITOR_ROWS = { minRows: 6, maxRows: 14 };
const REQUIRED = [{ required: true, whitespace: true, message: "请填写此项。" }];

export function DraftEditor() {
  const [form] = Form.useForm();
  const create = useCreateDraft();
  const feedback = useActionFeedback();
  async function submit(values: Record<string, unknown>) {
    return feedback.run(() => create.mutateAsync({ title: String(values.title).trim(),
      content: String(values.content).trim() }), "草稿已创建，审核通过后才能用于回答。");
  }
  return <WorkspacePanel title="编写标准答案" description="标题写客户的问题，正文写可核实的完整答案。">
    <GuidedForm form={form} onFinish={submit} submitLabel="创建待审核草稿" resetOnSuccess
      onValuesChange={feedback.clear} feedback={<ActionFeedback state={feedback} />} steps={[
        { title: "客户问题", fields: ["title"], content: <Form.Item name="title" label="问题标题" rules={REQUIRED}>
          <Input maxLength={TITLE_LIMIT} showCount placeholder="例如：如何申请退货？" />
        </Form.Item> },
        { title: "标准答案", fields: ["content"], content: <Form.Item name="content" label="标准答案" rules={REQUIRED}>
          <Input.TextArea autoSize={EDITOR_ROWS} placeholder="包含适用条件、处理步骤和必要说明" />
        </Form.Item> },
      ]} review={(values) => <dl><div><dt>客户问题</dt><dd>{String(values.title)}</dd></div>
        <div><dt>待审核答案</dt><dd>{String(values.content)}</dd></div></dl>} />
  </WorkspacePanel>;
}
