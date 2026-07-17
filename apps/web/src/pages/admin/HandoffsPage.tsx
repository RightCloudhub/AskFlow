import { useEffect, useState } from "react";
import { api } from "../../api/client";

type Handoff = {
  id: string;
  conversation_id: string;
  status: string;
  summary: string;
  claimed_by: string | null;
};

export function HandoffsPage() {
  const [rows, setRows] = useState<Handoff[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setRows(await api<Handoff[]>("/api/v1/admin/handoffs"));
  }

  useEffect(() => {
    void load().catch((e) => setError(String(e)));
  }, []);

  async function claim(id: string) {
    try {
      await api(`/api/v1/admin/handoffs/${id}/claim`, { method: "POST" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "claim failed");
    }
  }

  async function ret(id: string) {
    await api(`/api/v1/admin/handoffs/${id}/return`, { method: "POST" });
    await load();
  }

  return (
    <div className="page-shell tight">
      <h1>转人工收件箱</h1>
      {error && <div className="error-banner">{error}</div>}
      <ul className="data-list">
        {rows.map((h) => (
          <li key={h.id}>
            <div>
              <strong>{h.status}</strong>
              <div className="meta">conv={h.conversation_id}</div>
              <p>{h.summary}</p>
            </div>
            <div className="row-actions">
              <button type="button" onClick={() => void claim(h.id)}>
                认领
              </button>
              <button type="button" onClick={() => void ret(h.id)}>
                交还 AI
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
