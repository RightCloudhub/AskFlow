import { FormEvent, useEffect, useState } from "react";
import { getToken } from "../../api/client";
import { api } from "../../api/client";

type Doc = {
  id: string;
  title: string;
  filename: string;
  status: string;
  chunk_count: number;
};

export function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setDocs(await api<Doc[]>("/api/v1/admin/documents"));
  }

  useEffect(() => {
    void load().catch((e) => setError(String(e)));
  }, []);

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const token = getToken();
    const res = await fetch("/api/v1/embedding/upload", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    form.reset();
    await load();
  }

  async function onDelete(id: string) {
    await api(`/api/v1/admin/documents/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <div className="page-shell tight">
      <h1>知识文档</h1>
      <form className="panel form-grid" onSubmit={(e) => void onUpload(e)}>
        <input name="title" placeholder="标题（可选）" />
        <input name="file" type="file" required />
        <button type="submit">上传并索引</button>
      </form>
      {error && <div className="error-banner">{error}</div>}
      <ul className="data-list">
        {docs.map((d) => (
          <li key={d.id}>
            <div>
              <strong>{d.title}</strong>
              <div className="meta">
                {d.status} · chunks={d.chunk_count} · {d.filename}
              </div>
            </div>
            <button type="button" onClick={() => void onDelete(d.id)}>
              删除
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
