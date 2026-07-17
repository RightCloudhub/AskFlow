import { FormEvent, useEffect, useState } from "react";
import { api } from "../../api/client";

type Card = {
  id: string;
  title: string;
  status: string;
  expected_metrics: Record<string, number>;
  measured_metrics: Record<string, number>;
};

export function LaunchCardsPage() {
  const [rows, setRows] = useState<Card[]>([]);
  const [title, setTitle] = useState("");
  async function load() {
    setRows(await api<Card[]>("/api/v1/admin/launch-cards"));
  }
  useEffect(() => {
    void load();
  }, []);
  async function create(e: FormEvent) {
    e.preventDefault();
    await api("/api/v1/admin/launch-cards", {
      method: "POST",
      body: JSON.stringify({
        title,
        expected_metrics: { faq_resolve_rate: 0.7 },
      }),
    });
    setTitle("");
    await load();
  }
  return (
    <div className="page-shell tight">
      <h1>Launch Cards</h1>
      <form className="panel form-grid" onSubmit={(e) => void create(e)}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="变更标题" required />
        <button type="submit">创建</button>
      </form>
      <ul className="data-list">
        {rows.map((c) => (
          <li key={c.id}>
            <div>
              <strong>{c.title}</strong>
              <div className="meta">{c.status}</div>
              <pre>{JSON.stringify({ expected: c.expected_metrics, measured: c.measured_metrics })}</pre>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
