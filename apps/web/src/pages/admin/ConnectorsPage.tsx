import { useEffect, useState } from "react";
import { api } from "../../api/client";

type C = { name: string; base_url: string; enabled: boolean; description: string };

export function ConnectorsPage() {
  const [rows, setRows] = useState<C[]>([]);
  const [result, setResult] = useState("");
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
    setResult(JSON.stringify(r, null, 2));
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
      {result && (
        <pre className="panel">{result}</pre>
      )}
    </div>
  );
}
