import { useRef, useState } from "react";
import type { FormInstance } from "antd";
import type { ReactNode } from "react";

export type FormStep = { title: string; fields: string[]; content: ReactNode };
export type FlowOptions = {
  form: FormInstance; steps: FormStep[];
  onFinish: (values: Record<string, unknown>) => Promise<boolean | void>;
  resetOnSuccess?: boolean;
};

function errorStep(error: unknown, steps: FormStep[]) {
  const fields = (error as { errorFields?: { name: string[] }[] }).errorFields;
  const name = fields?.[0]?.name[0];
  return { name, index: steps.findIndex((step) => step.fields.includes(name ?? "")) };
}

export function useFormFlow({ form, steps, onFinish, resetOnSuccess }: FlowOptions) {
  const [current, setCurrent] = useState(0);
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const review = current === steps.length;
  async function validate() {
    const fields = review ? steps.flatMap((step) => step.fields) : steps[current].fields;
    try { await form.validateFields(fields); return true; }
    catch (error) {
      const failed = errorStep(error, steps);
      if (failed.index >= 0) setCurrent(failed.index);
      requestAnimationFrame(() => failed.name && form.scrollToField(failed.name, { focus: true }));
      return false;
    }
  }
  async function advance() {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    try {
      if (!await validate()) return;
      if (!review) { setCurrent(current + 1); return; }
      const saved = await onFinish(form.getFieldsValue(true));
      if (saved !== false && resetOnSuccess) { form.resetFields(); setCurrent(0); }
    } finally { locked.current = false; setBusy(false); }
  }
  return { current, review, busy, advance, goBack: (index: number) => {
    if (!locked.current && index >= 0 && index < current) setCurrent(index);
  } };
}
