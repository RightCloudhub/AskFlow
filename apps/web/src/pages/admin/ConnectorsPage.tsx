import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { JsonView } from "../../components/common/json";

type C = { name: string; base_url: string; enabled: boolean; description: string };

export function ConnectorsPage() {
  const [rows, setRows] = useState<C[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  async function load() {
    setRows(await api<C[]>("/api/v1/admin/connectors"));
  }
  useEffect(() => {
    void load();
  }, []);
  async function invoke(name: string) {
    const r = await api<Record<string, unknown>>(`/api/v1/admin/connectors/${name}/invoke`, {
      method: "POST",
      body: JSON.stringify({ params: {} }),
    });
    setResult(r);
  }
  return (
    <div className="page-shell tight">
      <h1>业务连接器</h1>
      <ul className="data-list">
        {rows.map((c) => (
          <li key={c.name}>
            <div>
              <strong>{c.name}</strong>
              <div className="meta">
                {c.base_url} · {c.enabled ? "on" : "off"}
              </div>
              <p>{c.description}</p>
            </div>
            <button type="button" onClick={() => void invoke(c.name)}>
              试调用
            </button>
          </li>
        ))}
      </ul>
      {result && <JsonView data={result} title="调用结果" />}
    </div>
  );
}
