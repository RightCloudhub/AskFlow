import { Button, Form } from "antd";
import type { ReactNode } from "react";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { FieldInput, fieldRules, submissionValues, type Field } from "./form-fields";

type ActionFormProps = {
  fields: Field[]; submit: (values: Record<string, unknown>) => Promise<unknown>;
  label: string; initial?: Record<string, unknown>; successMessage?: string;
  resetOnSuccess?: boolean; disabled?: boolean; extra?: ReactNode;
  onChange?: () => void;
};

export function ActionForm({ fields, submit, label, initial, successMessage, resetOnSuccess, disabled, extra, onChange }: ActionFormProps) {
  const [form] = Form.useForm();
  const feedback = useActionFeedback();
  async function finish(values: Record<string, unknown>) {
    const saved = await feedback.run(() => submit(submissionValues(values, fields)), successMessage ?? `${label}已完成。`);
    if (saved && resetOnSuccess) form.resetFields();
  }
  return <Form form={form} className="af-mall-form" layout="vertical" onFinish={finish}
    initialValues={initial} disabled={feedback.busy || disabled} scrollToFirstError={{ focus: true }}
    onValuesChange={() => { feedback.clear(); onChange?.(); }} requiredMark="optional">
    {fields.map((field) => <Form.Item key={field.name} name={field.name} label={field.label}
      extra={field.hint} rules={fieldRules(field)}>
      <FieldInput field={field} />
    </Form.Item>)}
    <div className="af-mall-form-actions"><div className="af-work-actions">
      <Button type="primary" htmlType="submit" loading={feedback.busy} disabled={disabled}>{label}</Button>{extra}
    </div><ActionFeedback state={feedback} /></div>
  </Form>;
}
