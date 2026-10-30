import { useRef, useState, type FormEvent, type DragEvent } from "react";
import { Button, Input } from "antd";
import { SettingsSection } from "../../components/admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useUploadDocument } from "../../hooks/use-documents";

const TEXT_FILE_TYPES = ".txt,.md,.csv,.json,text/plain,text/markdown,text/csv,application/json";
const BYTES_PER_KIB = 1024;

function useDocumentUpload() {
  const input = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File>();
  const [dragOver, setDragOver] = useState(false);
  const upload = useUploadDocument();
  const feedback = useActionFeedback();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    const body = new FormData();
    body.set("file", file);
    if (title.trim()) body.set("title", title.trim());
    const done = await feedback.run(() => upload.mutateAsync(body), "文件已上传，请在文档列表查看索引结果。");
    if (!done) return;
    setTitle(""); setFile(undefined);
    if (input.current) input.current.value = "";
  }
  function drop(event: DragEvent) {
    event.preventDefault(); setDragOver(false);
    if (!feedback.busy) setFile(event.dataTransfer.files[0]);
  }
  return { input, title, setTitle, file, setFile, dragOver, setDragOver, feedback, submit, drop };
}

export function DocumentUpload() {
  const state = useDocumentUpload();
  return <SettingsSection title="上传知识资料" description="先选择文件并确认标题，再提交索引。当前支持纯文本资料。">
    <ActionFeedback state={state.feedback} />
    <form onSubmit={(event) => void state.submit(event)}>
      <label className="af-field"><span>文档标题（可选）</span><Input value={state.title} disabled={state.feedback.busy}
        onChange={(event) => state.setTitle(event.target.value)} placeholder="留空时使用文件名" /></label>
      <button type="button" className={`af-upload-picker ${state.dragOver ? "dragover" : ""}`} disabled={state.feedback.busy}
        onClick={() => state.input.current?.click()} onDragOver={(event) => { event.preventDefault(); state.setDragOver(true); }}
        onDragLeave={() => state.setDragOver(false)} onDrop={state.drop} aria-describedby="af-document-file-hint">
        <strong>{state.file?.name ?? "选择或拖入知识文件"}</strong>
        <span>{state.file ? `${Math.ceil(state.file.size / BYTES_PER_KIB).toLocaleString("zh-CN")} KB · 点击可重新选择` : "TXT、Markdown、CSV 或 JSON"}</span>
      </button>
      <input className="af-work-file-input" ref={state.input} type="file" accept={TEXT_FILE_TYPES} aria-label="选择知识文件"
        onChange={(event) => { state.setFile(event.target.files?.[0]); state.feedback.clear(); }} />
      <p id="af-document-file-hint" className="af-work-help">请使用 UTF-8 或 GBK 编码的文字文件。文件大小上限由部署配置决定。</p>
      <div className="af-work-actions"><Button type="primary" htmlType="submit" loading={state.feedback.busy} disabled={!state.file}>上传并索引</Button>
        {state.file && <Button disabled={state.feedback.busy} onClick={() => {
          state.setFile(undefined); if (state.input.current) state.input.current.value = "";
        }}>移除已选文件</Button>}</div>
    </form>
  </SettingsSection>;
}
