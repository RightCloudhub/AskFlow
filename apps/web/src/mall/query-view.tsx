import { Button } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useState, type ReactNode } from "react";
import { Feedback } from "./shared";

type QueryView = { data?: unknown; error: string; loading: boolean; reload: () => Promise<void>; updatedAt?: Date };

export function MallQuery({ query, children }: { query: QueryView; children: ReactNode }) {
  return <div className="af-mall-query" aria-busy={query.loading}>
    <Feedback {...query} />{query.data !== undefined && children}
  </div>;
}

export function QueryRefresh({ query }: { query: QueryView }) {
  return <div className="af-mall-refresh">
    {query.updatedAt && <span>更新于 {query.updatedAt.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</span>}
    <Button type="text" icon={<ReloadOutlined />} loading={query.loading} onClick={() => void query.reload()}>刷新</Button>
  </div>;
}

export function useCursor() {
  const [history, setHistory] = useState([""]);
  return { cursor: history[history.length - 1], hasPrevious: history.length > 1,
    next: (cursor: string) => setHistory((pages) => [...pages, cursor]),
    previous: () => setHistory((pages) => pages.length > 1 ? pages.slice(0, -1) : pages) };
}

export function CursorNav({ paging, nextCursor, loading }: {
  paging: ReturnType<typeof useCursor>; nextCursor?: string | null; loading: boolean;
}) {
  if (!paging.hasPrevious && !nextCursor) return null;
  return <nav className="af-mall-pagination" aria-label="列表翻页">
    <Button disabled={!paging.hasPrevious || loading} onClick={paging.previous}>上一页</Button>
    <Button disabled={!nextCursor || loading} onClick={() => { if (nextCursor) paging.next(nextCursor); }}>下一页</Button>
  </nav>;
}
