import { useEffect, useState } from "react";
import { api } from "../../api/client";

type AnalyticsSummary = Record<string, unknown>;

function isScalar(value: unknown): value is string | number | boolean {
  return (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  );
}

function formatStat(value: string | number | boolean): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  return String(value);
}

export function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<AnalyticsSummary>("/api/v1/admin/analytics/summary")
      .then(setSummary)
      .catch((e) => setError(String(e)));
  }, []);

  const scalarStats = summary
    ? Object.entries(summary).filter(([, v]) => isScalar(v))
    : [];

  return (
    <div className="page-shell tight">
      <h1>运营看板</h1>
      {error && <div className="error-banner">{error}</div>}
      {summary && (
        <div className="stat-grid">
          {scalarStats.map(([k, v]) => (
            <div className="stat-card" key={k}>
              <div className="stat-label">{k}</div>
              <div className="stat-value">{formatStat(v as string | number | boolean)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
