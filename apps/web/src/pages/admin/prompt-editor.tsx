import { useRef, useState } from "react";
import { AutoComplete, Button, Form, Input, Popconfirm } from "antd";
import { QueryFeedback, SettingsSection } from "../../components/admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { GuidedForm } from "../../components/common/GuidedForm";
import { promptService } from "../../services/prompt-service";
import { usePromptTemplates, usePublishPrompt } from "../../hooks/use-ops";

const EDITOR_ROWS = { minRows: 8, maxRows: 20 };
const REQUIRED = [{ required: true, whitespace: true, message: "请填写此项。" }];

function usePromptEditor() {
  const [form] = Form.useForm();
  const [active, setActive] = useState<{ key: string; content: string }>();
  const [flowBusy, setFlowBusy] = useState(false);
  const drafts = useRef(new Map<string, string>());
  const selectedKey = useRef("rag.system");
  const publish = usePublishPrompt();
  const feedback = useActionFeedback();
  function selectKey(key: string) {
    drafts.current.set(selectedKey.current, String(form.getFieldValue("content") ?? ""));
    selectedKey.current = key;
    form.setFields([{ name: "content", value: drafts.current.get(key) ?? "", errors: [] }]);
    setActive(undefined); feedback.clear();
  }
  async function load() {
    const key = String(form.getFieldValue("key") ?? "").trim();
    if (!key) return;
    await feedback.run(async () => {
      const result = await promptService.active(key);
      setActive({ key, content: result.content });
      form.setFieldValue("content", result.content);
    }, "已载入当前生效版本。");
  }
  async function save(values: Record<string, unknown>) {
    const key = String(values.key).trim();
    const content = String(values.content);
    return feedback.run(async () => {
      await publish.mutateAsync({ key, content });
      setActive({ key, content });
    }, "新版本已发布并激活。");
  }
  return { form, active, feedback, load, save, selectKey, flowBusy, setFlowBusy };
}

export function PromptEditor() {
  const state = usePromptEditor();
  const templates = usePromptTemplates();
  const key = Form.useWatch("key", state.form);
  return <SettingsSection title="编辑提示词" description="选择模板、编辑正文，核对后发布生效。">
    <QueryFeedback query={templates} />
    <GuidedForm form={state.form} initialValues={{ key: "rag.system" }} submitLabel="发布并激活"
      onFinish={state.save} disabled={state.feedback.busy} onValuesChange={state.feedback.clear}
      onBusyChange={state.setFlowBusy}
      feedback={<ActionFeedback state={state.feedback} />} steps={[
        { title: "选择模板", fields: ["key"], content: <Form.Item name="key" label="模板键" rules={REQUIRED}>
          <AutoComplete onChange={state.selectKey} options={templates.data?.map((template) => ({ value: template.key, label: `${template.key} · ${template.description}` }))}
            filterOption={(input, option) => String(option?.value).includes(input)} placeholder="选择已有模板，或输入新模板键" />
        </Form.Item> },
        { title: "编辑正文", fields: ["content"], content: <>
          <Form.Item name="content" label="模板正文" rules={REQUIRED}>
            <Input.TextArea autoSize={EDITOR_ROWS} placeholder="填写完整的提示词正文" />
          </Form.Item>
          <Popconfirm title="载入当前生效版本？" description="编辑区内容将替换为当前生效正文。"
            okText="载入版本" cancelText="保留编辑" onConfirm={state.load} disabled={state.flowBusy || state.feedback.busy}>
            <Button disabled={!String(key ?? "").trim() || state.feedback.busy || state.flowBusy}>载入当前版本</Button>
          </Popconfirm>
        </> },
      ]} review={(values) => <dl><div><dt>模板键</dt><dd>{String(values.key)}</dd></div>
        <div><dt>发布后生效的正文</dt><dd>{String(values.content)}</dd></div>
        <div><dt>发布结果</dt><dd>{state.active?.content === values.content && state.active?.key === values.key
          ? "正文与已载入版本一致。" : "新正文将在发布后立即生效。"}</dd></div></dl>} />
  </SettingsSection>;
}
