import { useEffect, useId, useRef, type ReactNode } from "react";
import { Button, Form } from "antd";
import type { FormInstance } from "antd";
import { useFormFlow, type FormStep } from "./form-flow";
import "../../styles/form-flow.css";

type GuidedFormProps = {
  form: FormInstance; steps: FormStep[]; submitLabel: string;
  onFinish: (values: Record<string, unknown>) => Promise<boolean | void>;
  initialValues?: Record<string, unknown>; resetOnSuccess?: boolean;
  disabled?: boolean; feedback?: ReactNode; extra?: ReactNode;
  onValuesChange?: () => void;
  review: (values: Record<string, unknown>) => ReactNode;
};

export function GuidedForm(props: GuidedFormProps) {
  const flow = useFormFlow(props);
  const heading = useRef<HTMLHeadingElement>(null);
  const titleId = useId();
  const previous = useRef(flow.current);
  const busy = flow.busy || props.disabled;
  useEffect(() => {
    if (previous.current !== flow.current) heading.current?.focus();
    previous.current = flow.current;
  }, [flow.current]);
  return <Form form={props.form} layout="vertical" className="af-guided-form" initialValues={props.initialValues} aria-labelledby={titleId}
    disabled={busy} onValuesChange={props.onValuesChange} requiredMark="optional"
    onSubmitCapture={(event) => { event.preventDefault(); event.stopPropagation(); if (!busy) void flow.advance(); }}>
    <nav aria-label="填写进度"><ol className="af-form-progress">
      {[...props.steps.map((step) => step.title), "核对提交"].map((title, index) => <li key={title}
        aria-current={flow.current === index ? "step" : undefined} className={index < flow.current ? "complete" : ""}>
        <button type="button" disabled={busy || index >= flow.current} onClick={() => flow.goBack(index)}>{title}</button>
      </li>)}
    </ol></nav>
    <h3 id={titleId} tabIndex={-1} ref={heading} className="af-form-step-title">
      {flow.review ? "核对后提交" : props.steps[flow.current].title}
    </h3>
    {props.steps.map((step, index) => <div key={step.title} hidden={index !== flow.current}>{step.content}</div>)}
    {flow.review && <div className="af-form-review">{props.review(props.form.getFieldsValue(true))}</div>}
    <div className="af-form-flow-actions">
      {flow.current > 0 && <Button disabled={busy} onClick={() => flow.goBack(flow.current - 1)}>上一步</Button>}
      <Button type="primary" htmlType="submit" loading={flow.busy} disabled={props.disabled}>
        {flow.review ? props.submitLabel : "下一步"}
      </Button>{props.extra}
    </div>{props.feedback}
  </Form>;
}
