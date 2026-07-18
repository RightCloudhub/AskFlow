import { useState } from "react";
import { JsonNode } from "./JsonNode";
import { copyToClipboard, toPrettyJson } from "./jsonUtils";

const DEFAULT_EXPAND_DEPTH = 2;
const EXPAND_ALL_DEPTH = Number.MAX_SAFE_INTEGER;
const COLLAPSE_DEPTH = 0;
const ROOT_DEPTH = 0;
const COPY_FEEDBACK_MS = 1500;

export type JsonViewProps = {
  data: unknown;
  title?: string;
  initialExpandDepth?: number;
  /** Toolbar-less inline variant for use inside list rows. */
  compact?: boolean;
};

/**
 * Human-friendly JSON display: collapsible, syntax-coloured tree with a
 * toolbar (expand / collapse / raw / copy). Replaces raw <pre> JSON dumps.
 */
export function JsonView(props: JsonViewProps) {
  const [expandDepth, setExpandDepth] = useState(props.initialExpandDepth ?? DEFAULT_EXPAND_DEPTH);
  const [treeKey, setTreeKey] = useState(0);
  const [raw, setRaw] = useState(false);
  const [copied, setCopied] = useState(false);

  // Remount the tree so every node re-derives its open state from the new depth.
  function reflow(depth: number) {
    setExpandDepth(depth);
    setTreeKey((k) => k + 1);
  }

  async function onCopy() {
    const ok = await copyToClipboard(toPrettyJson(props.data));
    if (!ok) return;
    setCopied(true);
    window.setTimeout(() => setCopied(false), COPY_FEEDBACK_MS);
  }

  const tree = (
    <JsonNode key={treeKey} value={props.data} depth={ROOT_DEPTH} expandDepth={expandDepth} last />
  );

  if (props.compact) {
    return <div className="jv jv-compact">{tree}</div>;
  }

  return (
    <section className="jv" aria-label={props.title ?? "JSON"}>
      <Toolbar
        title={props.title}
        raw={raw}
        copied={copied}
        onExpand={() => reflow(EXPAND_ALL_DEPTH)}
        onCollapse={() => reflow(COLLAPSE_DEPTH)}
        onToggleRaw={() => setRaw((v) => !v)}
        onCopy={onCopy}
      />
      <div className="jv-body">{raw ? <RawBlock data={props.data} /> : tree}</div>
    </section>
  );
}

type ToolbarProps = {
  title?: string;
  raw: boolean;
  copied: boolean;
  onExpand: () => void;
  onCollapse: () => void;
  onToggleRaw: () => void;
  onCopy: () => void;
};

function Toolbar(p: ToolbarProps) {
  return (
    <header className="jv-bar">
      <span className="jv-title">{p.title ?? "数据"}</span>
      <div className="jv-actions">
        <button type="button" className="jv-btn" onClick={p.onExpand}>
          展开
        </button>
        <button type="button" className="jv-btn" onClick={p.onCollapse}>
          折叠
        </button>
        <button type="button" className="jv-btn" onClick={p.onToggleRaw}>
          {p.raw ? "树视图" : "原文"}
        </button>
        <button
          type="button"
          className={p.copied ? "jv-btn jv-copy is-done" : "jv-btn jv-copy"}
          onClick={p.onCopy}
        >
          {p.copied ? "已复制" : "复制"}
        </button>
      </div>
    </header>
  );
}

function RawBlock({ data }: { data: unknown }) {
  return <pre className="jv-raw">{toPrettyJson(data)}</pre>;
}
