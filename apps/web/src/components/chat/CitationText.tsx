import { Children, Fragment, type ReactNode } from "react";
import { Popover } from "antd";
import { ArrowRightOutlined, FileTextOutlined } from "@ant-design/icons";
import type { CitationSource } from "../../api/types";
import { useSourcePanel } from "../../stores/ui-store";

export function CitationTag({ source, index, sources }: {
  source: CitationSource; index: number; sources: CitationSource[];
}) {
  const openSources = useSourcePanel((state) => state.openSources);
  const title = source.source || `知识来源 ${index}`;
  const preview = <div className="af-citation-preview"><strong><FileTextOutlined />{title}</strong>
    <p>{source.text?.trim() || "该来源暂未提供摘要。"}</p>
    <button type="button" onClick={() => openSources(sources, "回答依据")}>查看完整依据<ArrowRightOutlined /></button>
  </div>;
  return <Popover content={preview} trigger={["hover", "focus"]} placement="top" arrow={false}>
    <button type="button" className="af-citation-tag" aria-label={`引用 ${index}：${title}`}
      onClick={() => openSources(sources, "回答依据")}>{index}</button>
  </Popover>;
}

function citedString(text: string, sources: CitationSource[]): ReactNode {
  return text.split(/(\[\d+\])/g).map((part, position) => {
    const match = /^\[(\d+)\]$/.exec(part);
    if (!match) return part;
    const index = Number(match[1]);
    const source = sources.find((row, offset) => (row.index ?? offset + 1) === index);
    if (!source) return part;
    return <CitationTag key={position} source={source} index={index} sources={sources} />;
  });
}

export function citationChildren(children: ReactNode, sources: CitationSource[]) {
  return Children.map(children, (child, index) => typeof child === "string" ?
    <Fragment key={index}>{citedString(child, sources)}</Fragment> : child);
}
