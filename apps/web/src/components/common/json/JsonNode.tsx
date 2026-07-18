import { useState } from "react";
import {
  BRACES,
  entriesOf,
  formatPrimitive,
  isContainer,
  kindOf,
  summaryLabel,
  type JsonEntry,
  type ValueKind,
} from "./jsonUtils";

export type JsonNodeProps = {
  label?: string;
  value: unknown;
  depth: number;
  expandDepth: number;
  last?: boolean;
};

/** Recursive renderer for one JSON value (leaf or container). */
export function JsonNode(props: JsonNodeProps) {
  const kind = kindOf(props.value);
  if (isContainer(kind)) {
    return <ContainerNode {...props} kind={kind} />;
  }
  return <PrimitiveRow label={props.label} value={props.value} kind={kind} last={props.last} />;
}

function KeyLabel({ label }: { label?: string }) {
  if (label === undefined) return null;
  return (
    <>
      <span className="jv-key">{label}</span>
      <span className="jv-punct jv-colon">:</span>
    </>
  );
}

type PrimitiveRowProps = { label?: string; value: unknown; kind: ValueKind; last?: boolean };

function PrimitiveRow({ label, value, kind, last }: PrimitiveRowProps) {
  return (
    <div className="jv-row">
      <KeyLabel label={label} />
      <span className={`jv-token jv-${kind}`}>{formatPrimitive(value, kind)}</span>
      {last ? null : <span className="jv-punct">,</span>}
    </div>
  );
}

type ContainerNodeProps = JsonNodeProps & { kind: ValueKind };

function ContainerNode({ label, value, kind, depth, expandDepth, last }: ContainerNodeProps) {
  const entries = entriesOf(value, kind);
  const [open, setOpen] = useState(depth < expandDepth);
  const [openBrace, closeBrace] = kind === "array" ? BRACES.array : BRACES.object;

  if (entries.length === 0) {
    return (
      <div className="jv-row">
        <KeyLabel label={label} />
        <span className="jv-punct">{openBrace + closeBrace}</span>
        {last ? null : <span className="jv-punct">,</span>}
      </div>
    );
  }

  return (
    <div className="jv-node">
      <div className="jv-row jv-head">
        <button
          className="jv-toggle"
          type="button"
          aria-expanded={open}
          aria-label={open ? "折叠" : "展开"}
          onClick={() => setOpen(!open)}
        >
          <span className="jv-caret" aria-hidden="true">
            {open ? "▾" : "▸"}
          </span>
        </button>
        <KeyLabel label={label} />
        {open ? (
          <span className="jv-punct">{openBrace}</span>
        ) : (
          <button className="jv-summary" type="button" onClick={() => setOpen(true)}>
            {summaryLabel(kind, entries.length)}
          </button>
        )}
      </div>
      {open ? <ChildList entries={entries} depth={depth} expandDepth={expandDepth} /> : null}
      {open ? (
        <div className="jv-row jv-foot">
          <span className="jv-punct">{closeBrace}</span>
          {last ? null : <span className="jv-punct">,</span>}
        </div>
      ) : null}
    </div>
  );
}

type ChildListProps = { entries: JsonEntry[]; depth: number; expandDepth: number };

function ChildList({ entries, depth, expandDepth }: ChildListProps) {
  return (
    <div className="jv-children">
      {entries.map((entry, i) => (
        <JsonNode
          key={entry.key}
          label={entry.key}
          value={entry.value}
          depth={depth + 1}
          expandDepth={expandDepth}
          last={i === entries.length - 1}
        />
      ))}
    </div>
  );
}
