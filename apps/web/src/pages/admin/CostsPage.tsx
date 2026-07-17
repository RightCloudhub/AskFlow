import { useEffect, useState } from "react";
import { api } from "../../api/client";

export function CostsPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    void api<Record<string, unknown>>("/api/v1/admin/costs/summary").then(setData);
  }, []);
  return (
    <div className="page-shell tight">
      <h1>成本汇总</h1>
      <pre className="panel">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}
