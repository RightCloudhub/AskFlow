import { useId, useRef, useState, type AriaAttributes } from "react";
import { Button } from "antd";

const TEXT_FILE_TYPES = ".txt,.md,.csv,.json,text/plain,text/markdown,text/csv,application/json";
const BYTES_PER_KIB = 1024;
type FilePickerProps = { id?: string; value?: File; onChange?: (file?: File) => void; disabled?: boolean }
  & Pick<AriaAttributes, "aria-describedby" | "aria-invalid">;

export function documentFileSize(file: File) {
  return `${Math.ceil(file.size / BYTES_PER_KIB).toLocaleString("zh-CN")} KB`;
}

export function DocumentFilePicker({ id, value, onChange, disabled, ...accessibility }: FilePickerProps) {
  const input = useRef<HTMLInputElement>(null);
  const hint = useId();
  const [dragOver, setDragOver] = useState(false);
  function choose(file?: File) { if (file && !disabled) onChange?.(file); }
  return <div>
    <button id={id} type="button" className={`af-upload-picker ${dragOver ? "dragover" : ""}`} disabled={disabled}
      onClick={() => input.current?.click()} onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragOver(true); }}
      onDragLeave={() => setDragOver(false)} onDrop={(event) => {
        event.preventDefault(); setDragOver(false); choose(event.dataTransfer.files[0]);
      }} aria-describedby={[hint, accessibility["aria-describedby"]].filter(Boolean).join(" ")}
      aria-invalid={accessibility["aria-invalid"]}>
      <strong>{value?.name ?? "选择或拖入知识文件"}</strong>
      <span>{value ? `${documentFileSize(value)} · 点击可重新选择` : "TXT、Markdown、CSV 或 JSON"}</span>
    </button>
    <input className="af-work-file-input" ref={input} type="file" accept={TEXT_FILE_TYPES} aria-label="选择知识文件"
      disabled={disabled} onChange={(event) => choose(event.target.files?.[0])} />
    <p id={hint} className="af-work-help">请使用 UTF-8 或 GBK 编码的文字文件。文件大小上限由部署配置决定。</p>
    {value && <Button disabled={disabled} onClick={() => { onChange?.(undefined); if (input.current) input.current.value = ""; }}>移除已选文件</Button>}
  </div>;
}
