import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { JsonView } from "../../components/common/json";

type RunRow = {
  run_id: string;
  route: string;
  intent: string | null;
  refused: boolean;
  flags: string[];
  steps: Array<{ kind: string; name: string; detail?: Record<string, unknown> }>;
  cost_summary: Record<string, unknown>;
  created_at?: string | null;
};

type RunDetail = RunRow & {
  cost?: {
    estimated_usd: number;
    entry_count: number;
    entries: Array<Record<string, unknown>>;
  };
};

export function AgentRunsPage() {
  const [rows, setRows] = useState<RunRow[]>([]);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [query, setQuery] = useState("");

  async function load() {
    setRows(await api<RunRow[]>("/api/v1/admin/agent-runs?limit=50"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function openRun(runId: string) {
    const d = await api<RunDetail>(`/api/v1/admin/agent-runs/${runId}`);
    setDetail(d);
    setQuery(runId);
  }

  async function lookup() {
    if (!query.trim()) return;
    await openRun(query.trim());
  }

  return (
    <div className="page-shell tight">
      <h1>Agent Run 回放</h1>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <label>
          run_id
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="run_…" />
        </label>
        <button type="button" onClick={() => void lookup()}>
          查询
        </button>
      </div>
      {detail ? (
        <div className="panel">
          <h2>{detail.run_id}</h2>
          <p className="meta">
            route={detail.route} · intent={detail.intent || "—"} · refused={String(detail.refused)}
          </p>
          <h3>步骤</h3>
          <ol>
            {(detail.steps || []).map((s, i) => (
              <li key={`${s.kind}-${s.name}-${i}`}>
                <strong>
                  [{s.kind}] {s.name}
                </strong>
                <JsonView data={s.detail || {}} compact initialExpandDepth={1} />
              </li>
            ))}
          </ol>
          <JsonView data={detail.cost || detail.cost_summary} title="费用" />
        </div>
      ) : null}
      <h2>最近 runs</h2>
      <ul className="data-list">
        {rows.map((r) => (
          <li key={r.run_id}>
            <div>
              <strong>{r.run_id}</strong>
              <div className="meta">
                {r.route} · {r.intent || "—"} · steps={(r.steps || []).length}
              </div>
            </div>
            <button type="button" onClick={() => void openRun(r.run_id)}>
              回放
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
