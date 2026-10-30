import { AutoComplete, DatePicker, Input, InputNumber, Radio, Select } from "antd";
import dayjs from "dayjs";
import type { Rule } from "antd/es/form";

import { currencySymbol, MONEY_DECIMALS } from "./money-values";

export { currencySymbol, MINOR_UNITS, MONEY_DECIMALS, submissionValues } from "./money-values";
const TEXTAREA_MIN_ROWS = 3;
const TEXTAREA_MAX_ROWS = 6;
export const PASSWORD_MIN_LENGTH = 12;
export const PASSWORD_HINT = "至少 12 位，包含大写字母、小写字母和数字。";
export const PASSWORD_RULES: Rule[] = [
  { min: PASSWORD_MIN_LENGTH, message: "密码至少需要 12 位。" },
  { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/, message: "请同时包含大写字母、小写字母和数字。" },
];

export type Field = {
  name: string; label: string; required?: boolean;
  kind?: "number" | "password" | "boolean" | "textarea" | "select" | "money" | "datetime" | "multiselect" | "suggest";
  step?: string; hidden?: boolean; readOnly?: boolean;
  hint?: string; placeholder?: string; autoComplete?: string;
  inputMode?: "text" | "tel" | "email" | "numeric";
  min?: number; max?: number; rules?: Rule[];
  options?: Array<{ value: string; label: string }>;
  currency?: string;
};

type InputProps = { field: Field; id?: string; value?: unknown; onChange?: (value: unknown) => void; "aria-describedby"?: string };

function NumberField({ field, ...props }: InputProps) {
  const money = field.kind === "money";
  return <InputNumber {...props} value={props.value as number} precision={money ? MONEY_DECIMALS : 0}
    min={field.min} max={field.max} prefix={money ? currencySymbol(field.currency) : undefined}
    placeholder={field.placeholder} style={{ width: "100%" }} />;
}

function fieldDescription({ field, ...props }: InputProps) {
  return props["aria-describedby"] ?? (field.hint && props.id ? `${props.id}_extra` : undefined);
}

function ChoiceField({ field, ...props }: InputProps) {
  if (field.kind === "boolean") return <Radio.Group {...props}
    options={[{ value: true, label: "是" }, { value: false, label: "否" }]} />;
  return <Select {...props} mode={field.kind === "multiselect" ? "multiple" : undefined}
    showSearch optionFilterProp="label" options={field.options}
    placeholder={field.placeholder ?? "请选择"} allowClear={field.required === false} />;
}

function TextField({ field, ...props }: InputProps) {
  const textProps = { ...props, value: props.value as string,
    placeholder: field.placeholder, autoComplete: field.autoComplete, inputMode: field.inputMode, readOnly: field.readOnly };
  if (field.kind === "password") return <Input.Password {...textProps} autoComplete={field.autoComplete ?? "current-password"} />;
  if (field.kind === "textarea") return <Input.TextArea {...textProps} autoSize={{ minRows: TEXTAREA_MIN_ROWS, maxRows: TEXTAREA_MAX_ROWS }} />;
  return <Input {...textProps} />;
}

export function FieldInput({ field, ...props }: InputProps) {
  const accessibility = { "aria-describedby": fieldDescription({ field, ...props }) };
  if (field.kind === "suggest") return <AutoComplete {...props} {...accessibility} value={props.value as string}
    options={field.options} placeholder={field.placeholder ?? "选择事件或输入事件名"}
    filterOption={(input, option) => `${option?.label} ${option?.value}`.toLowerCase().includes(input.toLowerCase())} />;
  if (field.kind === "datetime") return <DatePicker {...accessibility} id={props.id} showTime
    value={props.value ? dayjs(String(props.value)) : null} style={{ width: "100%" }}
    onChange={(value) => props.onChange?.(value?.toISOString())} />;
  if (["boolean", "select", "multiselect"].includes(field.kind ?? "")) return <ChoiceField field={field} {...props} {...accessibility} />;
  if (field.kind === "number" || field.kind === "money") return <NumberField field={field} {...props} {...accessibility} />;
  return <TextField field={field} {...props} {...accessibility} />;
}

export function fieldRules(field: Field): Rule[] {
  const whitespace = !field.kind || field.kind === "textarea";
  return [{ required: field.required !== false, whitespace,
    message: `${field.kind === "select" ? "请选择" : "请填写"}${field.label}。` }, ...(field.rules ?? [])];
}
