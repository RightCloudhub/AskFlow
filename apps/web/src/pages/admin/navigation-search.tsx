import { useEffect, useRef, useState } from "react";
import { Input, Modal } from "antd";
import { ArrowRightOutlined, SearchOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { NavSection } from "../../plugins/registry";
import { navIcon } from "../../components/admin";

function SearchResults({ sections, query, choose }: {
  sections: NavSection[]; query: string; choose: (path: string) => void;
}) {
  const matches = sections.flatMap(({ group, items }) => items.map((item) => ({ ...item, groupLabel: group.label })))
    .filter((item) => `${item.label} ${item.hint} ${item.groupLabel}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="af-navigation-results">
    {matches.map((item) => <button type="button" key={item.to} onClick={() => choose(item.to)}>
      {navIcon(item.icon)}<span><strong>{item.label}</strong><small>{item.groupLabel} · {item.hint}</small></span><ArrowRightOutlined />
    </button>)}
    {!matches.length && <p className="af-work-help">没有匹配的页面，试试其他关键词。</p>}
  </div>;
}

export function NavigationSearch({ sections }: { sections: NavSection[] }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const input = useRef<import("antd").InputRef>(null);
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "k") return;
      event.preventDefault();
      setOpen((value) => !value);
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  return <><button type="button" className="af-navigation-search" aria-keyshortcuts="Control+k Meta+k" onClick={() => setOpen(true)}>
    <SearchOutlined /><span>查找页面</span><kbd>⌘ / Ctrl K</kbd></button>
    <Modal title="前往管理页面" open={open} footer={null} onCancel={() => setOpen(false)}
      afterOpenChange={(visible) => { if (visible) input.current?.focus(); else setQuery(""); }}>
      <Input ref={input} value={query} onChange={(event) => setQuery(event.target.value)}
        prefix={<SearchOutlined />} placeholder="搜索知识、工单、商品、系统…" aria-label="搜索管理页面" allowClear />
      <SearchResults sections={sections} query={query} choose={(path) => { navigate(path); setOpen(false); }} />
    </Modal>
  </>;
}
