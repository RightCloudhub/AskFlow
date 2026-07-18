import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { JsonView } from "../../components/common/json";

type SlaStatus = {
  counts: Record<string, number>;
  tickets: Array<{
    id: string;
    title: string;
    priority: string;
    status: string;
    sla_state: string;
    created_at?: string | null;
  }>;
};

type ScanResult = {
  scanned_changes: number;
  changes: Array<{ ticket_id: string; previous: string; current: string; reason: string }>;
};

export function SlaPage() {
  const [status, setStatus] = useState<SlaStatus | null>(null);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setStatus(await api<SlaStatus>("/api/v1/admin/sla/status"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function runScan() {
    setBusy(true);
    try {
      const r = await api<ScanResult>("/api/v1/admin/sla/scan", { method: "POST" });
      setScan(r);
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-shell tight">
      <h1>SLA 运营</h1>
      <button type="button" disabled={busy} onClick={() => void runScan()}>
        {busy ? "扫描中…" : "立即扫描并通知"}
      </button>
      <JsonView data={status?.counts ?? {}} title="状态计数" />
      {scan ? (
        <JsonView data={scan.changes} title={`最近扫描 · ${scan.scanned_changes} 项变更`} />
      ) : null}
      <h2>Warning / Breached 工单</h2>
      <ul className="data-list">
        {(status?.tickets || []).map((t) => (
          <li key={t.id}>
            <div>
              <strong>{t.title}</strong>
              <div className="meta">
                {t.sla_state} · {t.priority} · {t.status}
              </div>
            </div>
          </li>
        ))}
      </ul>
      {!status?.tickets?.length ? <p className="meta">当前无 warning/breached 工单</p> : null}
    </div>
  );
}
