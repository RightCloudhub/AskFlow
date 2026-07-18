import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { JsonView } from "../../components/common/json";

type Audit = {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
};

export function AuditPage() {
  const [rows, setRows] = useState<Audit[]>([]);

  useEffect(() => {
    void api<Audit[]>("/api/v1/admin/audit-logs").then(setRows);
  }, []);

  return (
    <div className="page-shell tight">
      <h1>审计日志</h1>
      <ul className="data-list">
        {rows.map((a) => (
          <li key={a.id}>
            <div>
              <strong>{a.action}</strong>
              <div className="meta">
                {a.resource_type} {a.resource_id || ""} · {a.created_at}
              </div>
              <JsonView data={a.detail} compact initialExpandDepth={0} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
