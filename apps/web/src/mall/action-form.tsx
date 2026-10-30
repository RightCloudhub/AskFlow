import { Button, Form } from "antd";
import { useEffect, useId, type ReactNode } from "react";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { submissionValues, type Field } from "./form-fields";
import { GuidedForm, type FlowPrefix } from "../components/common/GuidedForm";
import { FormFields, FormReview, formSteps, LONG_FORM_FIELDS } from "./form-steps";

type ActionFormProps = {
  fields: Field[]; submit: (values: Record<string, unknown>) => Promise<unknown>;
  label: string; initial?: Record<string, unknown>; successMessage?: string;
  resetOnSuccess?: boolean; disabled?: boolean; extra?: ReactNode;
  onChange?: () => void;
  guided?: boolean;
  reviewContext?: ReactNode;
  onBusyChange?: (busy: boolean) => void;
  prefix?: FlowPrefix;
  active?: boolean;
  result?: ReactNode;
  onRestart?: () => void;
  restartLabel?: string;
};

export function ActionForm({ fields, submit, label, initial, successMessage, resetOnSuccess, disabled, extra, onChange, guided, reviewContext, onBusyChange, prefix, active, result, onRestart, restartLabel }: ActionFormProps) {
  const name = useId();
  const [form] = Form.useForm();
  const feedback = useActionFeedback();
  const useSteps = guided ?? (fields.length >= LONG_FORM_FIELDS || fields.some((field) => field.step));
  useEffect(() => { if (!useSteps) onBusyChange?.(feedback.busy); }, [feedback.busy, onBusyChange, useSteps]);
  async function finish(values: Record<string, unknown>) {
    const saved = await feedback.run(() => submit(submissionValues(values, fields)), successMessage ?? `${label}已完成。`);
    if (saved && resetOnSuccess && !useSteps) form.resetFields();
    return saved;
  }
  const changed = () => { feedback.clear(); onChange?.(); };
  if (useSteps) return <GuidedForm
    form={form} steps={formSteps(fields)} submitLabel={label} onFinish={finish} initialValues={initial}
    resetOnSuccess={resetOnSuccess} disabled={disabled} onValuesChange={changed} extra={extra}
    prefix={prefix} onBusyChange={onBusyChange} active={active}
    result={result} onRestart={onRestart} restartLabel={restartLabel}
    review={(values) => <>{reviewContext}<FormReview fields={fields} values={values} /></>}
    feedback={<ActionFeedback state={feedback} />} />;
  return <Form name={name} form={form} className="af-mall-form" layout="vertical" onFinish={finish}
    initialValues={initial} disabled={feedback.busy || disabled} scrollToFirstError={{ focus: true }}
    onValuesChange={changed} requiredMark="optional">
    <FormFields fields={fields} />
    <div className="af-mall-form-actions"><div className="af-form-flow-actions">
      {extra}<Button type="primary" htmlType="submit" loading={feedback.busy} disabled={disabled}>{label}</Button>
    </div><ActionFeedback state={feedback} /></div>
  </Form>;
}
