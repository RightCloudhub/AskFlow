import { useEffect, useState } from "react";
import { api } from "../../api/client";

type Ticket = {
  id: string;
  title: string;
  status: string;
  priority: string;
  type: string;
  assignee: string | null;
};

export function TicketsAdminPage() {
  const [rows, setRows] = useState<Ticket[]>([]);

  async function load() {
    setRows(await api<Ticket[]>("/api/v1/admin/tickets"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function setStatus(id: string, status: string) {
    await api(`/api/v1/admin/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    await load();
  }

  return (
    <div className="page-shell tight">
      <h1>工单看板</h1>
      <ul className="data-list">
        {rows.map((t) => (
          <li key={t.id}>
            <div>
              <strong>{t.title}</strong>
              <div className="meta">
                {t.status} · {t.priority} · {t.type}
              </div>
            </div>
            <div className="row-actions">
              <button type="button" onClick={() => void setStatus(t.id, "processing")}>
                处理中
              </button>
              <button type="button" onClick={() => void setStatus(t.id, "resolved")}>
                已解决
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
