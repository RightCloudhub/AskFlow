import { useEffect, useState } from "react";
import { api } from "../../api/client";

type IntentRow = {
  id: string;
  intent: string;
  route: string;
  enabled: boolean;
  description: string;
};

const INTENTS = ["faq", "product", "order_query", "fault_report", "complaint", "handoff"];
const ROUTES = ["rag", "tool", "ticket", "handoff", "clarify"];

export function IntentsPage() {
  const [rows, setRows] = useState<IntentRow[]>([]);
  const [intent, setIntent] = useState("faq");
  const [route, setRoute] = useState("rag");
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    setRows(await api<IntentRow[]>("/api/v1/admin/intents"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function save() {
    await api(`/api/v1/admin/intents/${intent}`, {
      method: "PUT",
      body: JSON.stringify({ intent, route, enabled: true, description: "ops" }),
    });
    setMsg(`已更新 ${intent} → ${route}`);
    await load();
  }

  return (
    <div className="page-shell tight">
      <h1>意图路由（热更新）</h1>
      <div className="panel form-grid">
        <label>
          Intent
          <select value={intent} onChange={(e) => setIntent(e.target.value)}>
            {INTENTS.map((i) => (
              <option key={i} value={i}>
                {i}
              </option>
            ))}
          </select>
        </label>
        <label>
          Route
          <select value={route} onChange={(e) => setRoute(e.target.value)}>
            {ROUTES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => void save()}>
          保存
        </button>
      </div>
      {msg && <p>{msg}</p>}
      <ul className="data-list">
        {rows.map((r) => (
          <li key={r.id}>
            <strong>{r.intent}</strong> → {r.route} {r.enabled ? "" : "(disabled)"}
          </li>
        ))}
      </ul>
    </div>
  );
}
