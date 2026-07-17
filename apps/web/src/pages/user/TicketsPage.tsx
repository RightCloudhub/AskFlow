import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";

type Ticket = {
  id: string;
  title: string;
  status: string;
  priority: string;
  type: string;
  description: string;
  created_at: string;
};

export function TicketsPage() {
  const [items, setItems] = useState<Ticket[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const rows = await api<Ticket[]>("/api/v1/tickets");
    setItems(rows);
  }

  useEffect(() => {
    void load().catch((e) => setError(String(e)));
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/api/v1/tickets", {
        method: "POST",
        body: JSON.stringify({ title, description, type: "user_created", priority: "medium" }),
      });
      setTitle("");
      setDescription("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  }

  async function closeTicket(id: string) {
    await api(`/api/v1/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "closed" }),
    });
    await load();
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <h1>我的工单</h1>
          <p>查看与关闭自己创建的工单</p>
        </div>
        <Link to="/">返回对话</Link>
      </header>

      <form className="panel form-grid" onSubmit={onCreate}>
        <h2>新建工单</h2>
        <input
          placeholder="标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          placeholder="描述"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
        <button type="submit">提交</button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <h2>工单列表</h2>
        <ul className="data-list">
          {items.map((t) => (
            <li key={t.id}>
              <div>
                <strong>{t.title}</strong>
                <div className="meta">
                  {t.status} · {t.priority} · {t.type}
                </div>
                <p>{t.description}</p>
              </div>
              {t.status !== "closed" && (
                <button type="button" onClick={() => void closeTicket(t.id)}>
                  关闭
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
