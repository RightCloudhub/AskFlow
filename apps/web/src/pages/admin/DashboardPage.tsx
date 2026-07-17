import { useEffect, useState } from "react";
import { api } from "../../api/client";

export function DashboardPage() {
  const [summary, setSummary] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Record<string, number>>("/api/v1/admin/analytics/summary")
      .then(setSummary)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="page-shell tight">
      <h1>运营看板</h1>
      {error && <div className="error-banner">{error}</div>}
      {summary && (
        <div className="stat-grid">
          {Object.entries(summary).map(([k, v]) => (
            <div className="stat-card" key={k}>
              <div className="stat-label">{k}</div>
              <div className="stat-value">{v}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
