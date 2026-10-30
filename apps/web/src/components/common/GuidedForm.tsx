import { useEffect, useId, type ReactNode } from "react";
import { Alert, Button, Form } from "antd";
import type { FormInstance } from "antd";
import { useFormFlow, type FormStep } from "./form-flow";
import { FlowFrame } from "./FlowFrame";

export type FlowPrefix = { titles: string[]; onBack: (index: number) => void };
type GuidedFormProps = {
  form: FormInstance; steps: FormStep[]; submitLabel: string;
  onFinish: (values: Record<string, unknown>) => Promise<boolean | void>;
  initialValues?: Record<string, unknown>; resetOnSuccess?: boolean;
  disabled?: boolean; feedback?: ReactNode; extra?: ReactNode;
  onValuesChange?: () => void;
  review?: (values: Record<string, unknown>) => ReactNode;
  prefix?: FlowPrefix;
  onBusyChange?: (busy: boolean) => void;
  active?: boolean;
  result?: ReactNode;
  onRestart?: () => void;
  restartLabel?: string;
};

function useGuidedNavigation(props: GuidedFormProps) {
  const flow = useFormFlow({ ...props, withReview: Boolean(props.review) });
  const busy = flow.busy || props.disabled;
  useEffect(() => { props.onBusyChange?.(flow.busy); }, [flow.busy, props.onBusyChange]);
  const offset = props.prefix?.titles.length ?? 0;
  const titles = [...props.prefix?.titles ?? [], ...props.steps.map((step) => step.title)];
  if (props.review) titles.push("核对提交");
  titles.push("操作结果");
  const current = flow.complete ? titles.length - 1 : offset + flow.current;
  function back(index: number) {
    if (busy || flow.complete) return;
    if (index < offset) props.prefix?.onBack(index); else flow.goBack(index - offset);
  }
  function restart() {
    if (busy) return;
    flow.restart(); props.onValuesChange?.(); props.onRestart?.();
  }
  return { flow, busy, current, titles, back, restart };
}

function CompletedForm({ props, restart, busy }: { props: GuidedFormProps; restart: () => void; busy?: boolean }) {
  return <div className="af-flow-success"><p role="status">本次提交已完成。</p>
    {props.result}{props.feedback}<div className="af-form-flow-actions">{props.extra}
      <Button disabled={busy} onClick={restart}>{props.restartLabel ?? (props.resetOnSuccess ? "继续填写" : "返回编辑")}</Button>
    </div>
  </div>;
}

type Navigation = ReturnType<typeof useGuidedNavigation>;

function FormControls({ props, navigation }: { props: GuidedFormProps; navigation: Navigation }) {
  const { flow, busy, current, back } = navigation;
  return <>
    {flow.review && <div className="af-form-review">{props.review?.(props.form.getFieldsValue(true))}</div>}
    {flow.error && <Alert type="error" showIcon title={flow.error} role="alert" />}
    <div className="af-form-flow-actions">
      {current > 0 && <Button disabled={busy} onClick={() => back(current - 1)}>上一步</Button>}
      {props.extra}<Button type="primary" htmlType="submit" loading={flow.busy} disabled={props.disabled}>
        {flow.last ? props.submitLabel : "下一步"}
      </Button>
    </div>{props.feedback}
  </>;
}

export function GuidedForm(props: GuidedFormProps) {
  const name = useId();
  const navigation = useGuidedNavigation(props);
  const { flow, busy, current, titles, back, restart } = navigation;
  return <Form name={name} form={props.form} layout="vertical" className="af-guided-form" initialValues={props.initialValues}
    disabled={busy} onValuesChange={() => { flow.clearError(); props.onValuesChange?.(); }} requiredMark="optional"
    onSubmitCapture={(event) => { event.preventDefault(); event.stopPropagation(); if (!busy) void flow.advance(); }}>
    <FlowFrame titles={titles} current={current} busy={busy} onBack={back} active={props.active}
      backDisabled={flow.complete} title={flow.complete ? "操作已完成" : flow.review ? "核对后提交" : undefined}
      description={flow.complete ? undefined : props.steps[flow.current]?.description}>
      {props.steps.map((step, index) => <div key={step.title} hidden={flow.complete || index !== flow.current}>{step.content}</div>)}
      {flow.complete ? <CompletedForm props={props} restart={restart} busy={busy} /> : <FormControls props={props} navigation={navigation} />}
    </FlowFrame>
  </Form>;
}
