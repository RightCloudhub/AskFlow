import { Button, Form } from "antd";
import type { ReactNode } from "react";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { submissionValues, type Field } from "./form-fields";
import { GuidedForm } from "../components/common/GuidedForm";
import { FormFields, FormReview, formSteps, LONG_FORM_FIELDS } from "./form-steps";

type ActionFormProps = {
  fields: Field[]; submit: (values: Record<string, unknown>) => Promise<unknown>;
  label: string; initial?: Record<string, unknown>; successMessage?: string;
  resetOnSuccess?: boolean; disabled?: boolean; extra?: ReactNode;
  onChange?: () => void;
  guided?: boolean;
  reviewContext?: ReactNode;
};

export function ActionForm({ fields, submit, label, initial, successMessage, resetOnSuccess, disabled, extra, onChange, guided, reviewContext }: ActionFormProps) {
  const [form] = Form.useForm();
  const feedback = useActionFeedback();
  const useSteps = guided ?? (fields.length >= LONG_FORM_FIELDS || fields.some((field) => field.step));
  async function finish(values: Record<string, unknown>) {
    const saved = await feedback.run(() => submit(submissionValues(values, fields)), successMessage ?? `${label}已完成。`);
    if (saved && resetOnSuccess && !useSteps) form.resetFields();
    return saved;
  }
  const changed = () => { feedback.clear(); onChange?.(); };
  if (useSteps) return <GuidedForm
    form={form} steps={formSteps(fields)} submitLabel={label} onFinish={finish} initialValues={initial}
    resetOnSuccess={resetOnSuccess} disabled={disabled} onValuesChange={changed} extra={extra}
    review={(values) => <>{reviewContext}<FormReview fields={fields} values={values} /></>}
    feedback={<ActionFeedback state={feedback} />} />;
  return <Form form={form} className="af-mall-form" layout="vertical" onFinish={finish}
    initialValues={initial} disabled={feedback.busy || disabled} scrollToFirstError={{ focus: true }}
    onValuesChange={changed} requiredMark="optional">
    <FormFields fields={fields} />
    <div className="af-mall-form-actions"><div className="af-work-actions">
      <Button type="primary" htmlType="submit" loading={feedback.busy} disabled={disabled}>{label}</Button>{extra}
    </div><ActionFeedback state={feedback} /></div>
  </Form>;
}
