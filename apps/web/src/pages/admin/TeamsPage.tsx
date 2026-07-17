import { useEffect, useState } from "react";
import { api } from "../../api/client";

type Team = {
  id: string;
  name: string;
  description: string;
  intent_scope: string;
  member_ids?: string[];
  member_count?: number;
};

type UserRow = { id: string; username: string; email: string; role: string };

export function TeamsPage() {
  const [rows, setRows] = useState<Team[]>([]);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [name, setName] = useState("");
  const [scope, setScope] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    const [teams, us] = await Promise.all([
      api<Team[]>("/api/v1/admin/teams"),
      api<UserRow[]>("/api/v1/admin/users"),
    ]);
    setRows(teams);
    setUsers(us);
  }

  useEffect(() => {
    void load();
  }, []);

  async function createTeam() {
    if (!name.trim()) return;
    await api("/api/v1/admin/teams", {
      method: "POST",
      body: JSON.stringify({ name: name.trim(), intent_scope: scope.trim(), description: "" }),
    });
    setName("");
    setScope("");
    setMsg("已创建技能组");
    await load();
  }

  async function addMember(teamId: string, userId: string) {
    if (!userId) return;
    await api(`/api/v1/admin/teams/${teamId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    });
    setMsg("已添加成员");
    await load();
  }

  return (
    <div className="page-shell tight">
      <h1>技能组 Teams</h1>
      {msg ? <p className="meta">{msg}</p> : null}
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <h2>新建</h2>
        <label>
          名称
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          意图范围 (逗号分隔)
          <input value={scope} onChange={(e) => setScope(e.target.value)} placeholder="faq,order" />
        </label>
        <button type="button" onClick={() => void createTeam()}>
          创建
        </button>
      </div>
      <ul className="data-list">
        {rows.map((t) => (
          <li key={t.id}>
            <div>
              <strong>{t.name}</strong>
              <div className="meta">
                scope={t.intent_scope || "—"} · members={t.member_count ?? 0}
              </div>
              <div className="meta">{(t.member_ids || []).join(", ") || "无成员"}</div>
            </div>
            <select
              defaultValue=""
              onChange={(e) => {
                const uid = e.target.value;
                e.target.value = "";
                if (uid) void addMember(t.id, uid);
              }}
            >
              <option value="">+ 成员</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.username} ({u.role})
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </div>
  );
}
