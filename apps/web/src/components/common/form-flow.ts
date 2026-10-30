import { useRef, useState } from "react";
import type { FormInstance } from "antd";
import type { ReactNode } from "react";
import { readableError } from "./error-text";

export type FormStep = { title: string; description?: string; fields: string[]; content: ReactNode };
export type FlowOptions = {
  form: FormInstance; steps: FormStep[];
  onFinish: (values: Record<string, unknown>) => Promise<boolean | void>;
  resetOnSuccess?: boolean;
  withReview?: boolean;
};

function errorStep(error: unknown, steps: FormStep[]) {
  const fields = (error as { errorFields?: { name: string[] }[] }).errorFields;
  const name = fields?.[0]?.name[0];
  return { name, index: steps.findIndex((step) => step.fields.includes(name ?? "")) };
}

export function useFormFlow({ form, steps, onFinish, resetOnSuccess, withReview = true }: FlowOptions) {
  const [current, setCurrent] = useState(0);
  const [busy, setBusy] = useState(false);
  const [complete, setComplete] = useState(false);
  const locked = useRef(false);
  const [error, setError] = useState("");
  const review = withReview && current === steps.length;
  const last = current === steps.length - (withReview ? 0 : 1);
  async function validate() {
    const fields = last ? steps.flatMap((step) => step.fields) : steps[current].fields;
    try { await form.validateFields(fields); return true; }
    catch (error) {
      const failed = errorStep(error, steps);
      if (failed.index >= 0) setCurrent(failed.index);
      requestAnimationFrame(() => failed.name && form.scrollToField(failed.name, { focus: true }));
      return false;
    }
  }
  async function advance() {
    if (locked.current || complete) return;
    locked.current = true;
    setError("");
    setBusy(true);
    try {
      if (!await validate()) return;
      if (!last) { setCurrent(current + 1); return; }
      const saved = await onFinish(form.getFieldsValue(true));
      if (saved === false) return;
      setComplete(true);
      if (resetOnSuccess) form.resetFields();
    } catch (reason) { setError(readableError(reason)); }
    finally { locked.current = false; setBusy(false); }
  }
  return { current, review, last, busy, error, complete, advance, clearError: () => setError(""),
    restart: () => { if (!locked.current) { setComplete(false); setCurrent(0); setError(""); } },
    goBack: (index: number) => {
      if (!locked.current && !complete && index >= 0 && index < current) { setCurrent(index); setError(""); }
    } };
}
