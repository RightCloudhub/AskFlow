import { useState } from "react";
import { Form, Input } from "antd";
import { SettingsSection } from "../../components/admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { GuidedForm } from "../../components/common/GuidedForm";
import { useUploadDocument } from "../../hooks/use-documents";
import { DocumentFilePicker, documentFileSize } from "./document-file-picker";

function UploadReview({ values }: { values: Record<string, unknown> }) {
  const file = values.file as File | undefined;
  return <dl><div><dt>文件</dt><dd>{file?.name}</dd></div>
    <div><dt>文件大小</dt><dd>{file ? documentFileSize(file) : "未选择"}</dd></div>
    <div><dt>文档标题</dt><dd>{String(values.title ?? "").trim() || file?.name}</dd></div>
    <div><dt>提交后</dt><dd>文件将上传并建立知识索引，可在文档列表查看处理结果。</dd></div>
  </dl>;
}

export function DocumentUpload() {
  const [form] = Form.useForm();
  const [busy, setBusy] = useState(false);
  const upload = useUploadDocument();
  const feedback = useActionFeedback();
  async function submit(values: Record<string, unknown>) {
    if (!(values.file instanceof File)) return false;
    const body = new FormData();
    body.set("file", values.file);
    const title = String(values.title ?? "").trim();
    if (title) body.set("title", title);
    return feedback.run(() => upload.mutateAsync(body), "文件已上传，请在文档列表查看索引结果。");
  }
  return <SettingsSection title="上传知识资料" description="选择资料、确认标题，再提交知识索引。">
    <GuidedForm form={form} onFinish={submit} submitLabel="上传并索引" resetOnSuccess onBusyChange={setBusy}
      onValuesChange={feedback.clear} feedback={<ActionFeedback state={feedback} />} steps={[
        { title: "选择文件", fields: ["file"], content: <Form.Item name="file" label="知识文件"
          rules={[{ required: true, message: "请选择要上传的知识文件。" }]}><DocumentFilePicker disabled={busy} /></Form.Item> },
        { title: "文档信息", fields: ["title"], content: <Form.Item name="title" label="文档标题（可选）" extra="留空时使用文件名。">
          <Input placeholder="为资料填写容易查找的标题" /></Form.Item> },
      ]} review={(values) => <UploadReview values={values} />} />
  </SettingsSection>;
}
