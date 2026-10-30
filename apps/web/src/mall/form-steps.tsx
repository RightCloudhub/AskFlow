import { Form } from "antd";
import { FieldInput, fieldRules, type Field } from "./form-fields";

const FIELDS_PER_STEP = 3;
export const LONG_FORM_FIELDS = 4;

export function FormFields({ fields }: { fields: Field[] }) {
  return <>{fields.map((field) => <Form.Item key={field.name} name={field.name} label={field.label}
    extra={field.hint} rules={fieldRules(field)} hidden={field.hidden} dependencies={field.dependencies}>
    <FieldInput field={field} />
  </Form.Item>)}</>;
}

export function formSteps(fields: Field[]) {
  const groups = new Map<string, Field[]>();
  const visible = fields.filter((field) => !field.hidden);
  visible.forEach((field, index) => {
    const group = Math.floor(index / FIELDS_PER_STEP);
    const title = field.step ?? ["基本信息", "补充信息"][group] ?? visible[group * FIELDS_PER_STEP].label;
    groups.set(title, [...groups.get(title) ?? [], field]);
  });
  return Array.from(groups, ([title, group], index) => {
    const registered = index === 0 ? [...fields.filter((field) => field.hidden), ...group] : group;
    return { title, fields: registered.map((field) => field.name), content: <FormFields fields={registered} /> };
  });
}

function displayValue(field: Field, value: unknown) {
  if (value === undefined || value === null || value === "") return "未填写";
  if (field.kind === "password") return "已填写";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (Array.isArray(value)) return value.map((item) => field.options?.find((option) => option.value === item)?.label ?? item).join("、") || "未选择";
  return field.options?.find((option) => option.value === value)?.label ?? String(value);
}

export function FormReview({ fields, values }: { fields: Field[]; values: Record<string, unknown> }) {
  return <dl>{fields.filter((field) => !field.hidden).map((field) => <div key={field.name}>
    <dt>{field.label}</dt><dd>{displayValue(field, values[field.name])}</dd>
  </div>)}</dl>;
}
