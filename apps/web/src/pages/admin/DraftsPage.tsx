import { FormEvent, useEffect, useState } from "react";
import { api } from "../../api/client";

type Draft = {
  id: string;
  title: string;
  content: string;
  status: string;
  document_id: string | null;
};

export function DraftsPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  async function load() {
    setDrafts(await api<Draft[]>("/api/v1/admin/drafts"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    await api("/api/v1/admin/drafts", {
      method: "POST",
      body: JSON.stringify({ title, content }),
    });
    setTitle("");
    setContent("");
    await load();
  }

  async function approve(id: string) {
    await api(`/api/v1/admin/drafts/${id}/approve`, { method: "POST" });
    await load();
  }

  async function reject(id: string) {
    await api(`/api/v1/admin/drafts/${id}/reject`, { method: "POST" });
    await load();
  }

  return (
    <div className="page-shell tight">
      <h1>知识草稿</h1>
      <form className="panel form-grid" onSubmit={(e) => void create(e)}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="标题" required />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="正文"
          rows={4}
          required
        />
        <button type="submit">创建草稿</button>
      </form>
      <ul className="data-list">
        {drafts.map((d) => (
          <li key={d.id}>
            <div>
              <strong>{d.title}</strong>
              <div className="meta">
                {d.status}
                {d.document_id ? ` · doc=${d.document_id}` : ""}
              </div>
              <p>{d.content.slice(0, 160)}</p>
            </div>
            {d.status === "draft" && (
              <div className="row-actions">
                <button type="button" onClick={() => void approve(d.id)}>
                  审核通过
                </button>
                <button type="button" onClick={() => void reject(d.id)}>
                  拒绝
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
