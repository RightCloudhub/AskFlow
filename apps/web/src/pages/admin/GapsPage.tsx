import { useEffect, useState } from "react";
import { api } from "../../api/client";

type Gap = {
  id: string;
  question: string;
  hit_count: number;
  reason: string | null;
  status: string;
};

export function GapsPage() {
  const [gaps, setGaps] = useState<Gap[]>([]);

  async function load() {
    setGaps(await api<Gap[]>("/api/v1/admin/gaps"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function dismiss(id: string) {
    await api(`/api/v1/admin/gaps/${id}/dismiss`, { method: "POST" });
    await load();
  }

  async function promote(g: Gap) {
    await api(`/api/v1/admin/gaps/${g.id}/promote`, {
      method: "POST",
      body: JSON.stringify({
        title: `FAQ: ${g.question.slice(0, 40)}`,
        content: g.question,
        gap_id: g.id,
      }),
    });
    await load();
  }

  return (
    <div className="page-shell tight">
      <h1>知识缺口</h1>
      <ul className="data-list">
        {gaps.map((g) => (
          <li key={g.id}>
            <div>
              <strong>{g.question}</strong>
              <div className="meta">
                hits={g.hit_count} · {g.reason || "-"}
              </div>
            </div>
            <div className="row-actions">
              <button type="button" onClick={() => void promote(g)}>
                生成草稿
              </button>
              <button type="button" onClick={() => void dismiss(g.id)}>
                忽略
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
