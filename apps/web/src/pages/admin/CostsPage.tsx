import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { JsonView } from "../../components/common/json";

export function CostsPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    void api<Record<string, unknown>>("/api/v1/admin/costs/summary").then(setData);
  }, []);
  return (
    <div className="page-shell tight">
      <h1>成本汇总</h1>
      {data ? <JsonView data={data} title="成本汇总" /> : <p className="meta">加载中…</p>}
    </div>
  );
}
