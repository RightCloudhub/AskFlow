import { useEffect, useState } from "react";
import { api } from "../../api/client";

type Template = { id: string; key: string; description: string; active_version_id: string | null };

export function PromptsPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [key, setKey] = useState("rag.system");
  const [content, setContent] = useState("");
  const [active, setActive] = useState("");

  async function load() {
    setTemplates(await api<Template[]>("/api/v1/admin/prompts"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function loadActive() {
    const res = await api<{ content: string }>(`/api/v1/admin/prompts/${key}/active`);
    setActive(res.content);
    setContent(res.content);
  }

  async function publish() {
    await api(`/api/v1/admin/prompts/${key}/versions`, {
      method: "POST",
      body: JSON.stringify({ content, activate: true }),
    });
    await load();
    await loadActive();
  }

  return (
    <div className="page-shell tight">
      <h1>Prompt 模板</h1>
      <div className="panel form-grid">
        <input value={key} onChange={(e) => setKey(e.target.value)} />
        <button type="button" onClick={() => void loadActive()}>
          加载 active
        </button>
        <textarea rows={6} value={content} onChange={(e) => setContent(e.target.value)} />
        <button type="button" onClick={() => void publish()}>
          发布并激活
        </button>
      </div>
      {active && (
        <div className="panel">
          <h3>当前 active</h3>
          <pre>{active}</pre>
        </div>
      )}
      <ul className="data-list">
        {templates.map((t) => (
          <li key={t.id}>
            <strong>{t.key}</strong> · {t.description}
          </li>
        ))}
      </ul>
    </div>
  );
}
