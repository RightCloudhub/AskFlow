import { useEffect, useState } from "react";
import { api } from "../../api/client";

type U = { id: string; username: string; email: string; role: string; is_active: boolean };

export function UsersPage() {
  const [rows, setRows] = useState<U[]>([]);
  async function load() {
    setRows(await api<U[]>("/api/v1/admin/users"));
  }
  useEffect(() => {
    void load();
  }, []);
  async function toggle(u: U) {
    await api(`/api/v1/admin/users/${u.id}/active`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    await load();
  }
  return (
    <div className="page-shell tight">
      <h1>用户管理</h1>
      <ul className="data-list">
        {rows.map((u) => (
          <li key={u.id}>
            <div>
              <strong>{u.username}</strong>
              <div className="meta">
                {u.email} · {u.role} · {u.is_active ? "active" : "disabled"}
              </div>
            </div>
            <button type="button" onClick={() => void toggle(u)}>
              {u.is_active ? "禁用" : "启用"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
