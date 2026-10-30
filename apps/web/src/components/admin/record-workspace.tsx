import type { ReactNode } from "react";
import { WorkspacePanel } from "./workspace";

type StateOption = { value: string; label: string };
type RecordWorkspaceProps = {
  rows?: object[]; states: StateOption[]; field?: string; selected?: string;
  onSelect?: (value: string) => void; children: ReactNode; title?: string;
};

export function RecordWorkspace({ rows, states, field = "status", selected, onSelect, children, title = "记录概况" }: RecordWorkspaceProps) {
  const options = [{ value: "all", label: "全部记录" }, ...states];
  const counts = options.map((option) => ({ ...option, count: rows == null ? null : option.value === "all" ? rows.length :
    rows.filter((row) => String((row as Record<string, unknown>)[field]) === option.value).length }));
  return <div className="af-record-workspace"><aside className="af-record-sidebar">
    <WorkspacePanel title={title} description="按当前已加载记录统计。"><div className="af-record-summary">
      {counts.map((option) => onSelect ? <button key={option.value} type="button" aria-pressed={selected === option.value}
        onClick={() => onSelect(option.value)}><span>{option.label}</span><strong>{option.count ?? "—"}</strong></button> :
        <div key={option.value}><span>{option.label}</span><strong>{option.count ?? "—"}</strong></div>)}
    </div></WorkspacePanel>
  </aside><div className="af-record-main">{children}</div></div>;
}

export function ConfigurationWorkspace({ editor, children, wideEditor = false }: {
  editor: ReactNode; children: ReactNode; wideEditor?: boolean;
}) {
  return <div className={`af-config-workspace ${wideEditor ? "af-config-workspace--wide" : ""}`}><div className="af-config-records">{children}</div>
    <aside className="af-config-editor">{editor}</aside>
  </div>;
}
