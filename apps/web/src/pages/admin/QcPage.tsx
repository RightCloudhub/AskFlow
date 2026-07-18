import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { JsonView } from "../../components/common/json";

type Summary = Record<string, number | null>;
type LowRun = {
  run_id: string;
  route: string;
  intent: string | null;
  refused: boolean;
  score: number;
  flags: string[];
};

export function QcPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [runs, setRuns] = useState<LowRun[]>([]);

  useEffect(() => {
    void (async () => {
      setSummary(await api<Summary>("/api/v1/admin/qc/summary"));
      const low = await api<{ runs: LowRun[] }>("/api/v1/admin/qc/low-quality?limit=30");
      setRuns(low.runs || []);
    })();
  }, []);

  return (
    <div className="page-shell tight">
      <h1>质检 QC</h1>
      <p className="meta">基于拒答、弱证据 flags、反馈的确定性评分（无二次 LLM）</p>
      {summary ? <JsonView data={summary} title="质检汇总" /> : <p className="meta">加载中…</p>}
      <h2>低分 / 拒答 runs</h2>
      <ul className="data-list">
        {runs.map((r) => (
          <li key={r.run_id}>
            <div>
              <strong>{r.run_id}</strong>
              <div className="meta">
                score={r.score} · {r.route} · {r.intent || "—"} · refused={String(r.refused)}
              </div>
              <div className="meta">{(r.flags || []).join(", ")}</div>
            </div>
          </li>
        ))}
      </ul>
      {!runs.length ? <p className="meta">暂无低分记录</p> : null}
    </div>
  );
}
