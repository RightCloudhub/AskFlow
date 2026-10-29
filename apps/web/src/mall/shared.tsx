import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Form, Input, InputNumber, Radio, Space, Spin } from "antd";

export type Row = Record<string, unknown>;
export type Page<T> = { items: T[]; next_cursor?: string | null };
export type Field = { name: string; label: string; kind?: "number" | "password" | "boolean"; required?: boolean };

function fieldInput(field: Field) {
  if (field.kind === "number") return <InputNumber precision={0} style={{ width: "100%" }} />;
  if (field.kind === "boolean") return <Radio.Group options={[{ value: true, label: "是" }, { value: false, label: "否" }]} />;
  if (field.kind === "password") return <Input.Password autoComplete="off" />;
  return <Input />;
}

export function useLoad<T>(loader: () => Promise<T>) {
  const generation = useRef(0);
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const reload = useCallback(async () => {
    const request = ++generation.current;
    setLoading(true);
    try {
      const result = await loader();
      if (request === generation.current) { setData(result); setError(""); }
    } catch (reason) {
      if (request === generation.current) setError(reason instanceof Error ? reason.message : "加载失败");
    } finally { if (request === generation.current) setLoading(false); }
  }, [loader]);
  useEffect(() => {
    setData(undefined);
    void reload();
    return () => { generation.current += 1; };
  }, [reload]);
  return { data, error, loading, reload };
}

export function Feedback({ error, loading }: { error?: string; loading?: boolean }) {
  return <>{error && <Alert type="error" title={error} showIcon />}{loading && <Spin />}</>;
}

export function ActionForm({ fields, submit, label, initial }: {
  fields: Field[]; submit: (values: Row) => Promise<unknown>; label: string; initial?: Row;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  async function finish(values: Row) {
    setBusy(true); setError(""); setSuccess(false);
    try { await submit(values); setSuccess(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败"); }
    finally { setBusy(false); }
  }
  return <Form layout="vertical" onFinish={finish} initialValues={initial}>
    {fields.map((field) => <Form.Item key={field.name} name={field.name} label={field.label}
      rules={[{ required: field.required !== false }]}>
      {fieldInput(field)}
    </Form.Item>)}
    <Space direction="vertical"><Button type="primary" htmlType="submit" loading={busy}>{label}</Button>
      <Feedback error={error} />{success && <Alert type="success" title="操作已保存" />}</Space>
  </Form>;
}
