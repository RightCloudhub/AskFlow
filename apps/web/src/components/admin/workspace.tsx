import { Button, Input, Select, Table, Alert } from "antd";
import type { TableProps } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";
import { readableError } from "../common/action-feedback";
import { DESIGN } from "../../design/tokens";

export const RECORD_PAGE_SIZE = 10;
export type QueryPresentation = {
  isLoading: boolean; isFetching: boolean; isError: boolean;
  error: unknown; refetch: () => Promise<unknown>;
};
type PanelProps = { title: string; description?: string; actions?: ReactNode; children: ReactNode; className?: string };

export function WorkspacePanel({ title, description, actions, children, className = "" }: PanelProps) {
  return <section className={`af-work-panel ${className}`}>
    <header className="af-work-panel-head"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{actions}</header>
    {children}
  </section>;
}

export function SettingsSection({ title, description, children }: PanelProps) {
  return <section className="af-work-settings"><div><h2>{title}</h2><p>{description}</p></div>
    <div className="af-work-settings-body">{children}</div>
  </section>;
}

export function RefreshButton({ query }: { query: QueryPresentation }) {
  return <Button icon={<ReloadOutlined />} loading={query.isFetching} onClick={() => void query.refetch()}>刷新数据</Button>;
}

export function QueryFeedback({ query }: { query: QueryPresentation }) {
  if (!query.isError) return null;
  return <div className="af-action-notice" role="status"><Alert type="error" showIcon title="数据暂时无法读取"
    description={readableError(query.error)} action={<Button loading={query.isFetching} onClick={() => void query.refetch()}>重新加载</Button>} />
  </div>;
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="af-work-empty"><h3>{title}</h3>{description && <p>{description}</p>}{action}</div>;
}

type DataTableProps<T extends object> = TableProps<T> & {
  query?: QueryPresentation; emptyTitle: string; emptyDescription?: string; emptyAction?: ReactNode;
};

export function DataTable<T extends object>({ query, emptyTitle, emptyDescription, emptyAction, ...props }: DataTableProps<T>) {
  const empty = query?.isError ? "数据未加载，请重试。" : query?.isLoading ? "正在读取数据…" :
    <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />;
  return <div className="af-work-table">{query && <QueryFeedback query={query} />}
    <Table<T> rowKey="id" size="middle" pagination={{ defaultPageSize: RECORD_PAGE_SIZE, showSizeChanger: false,
      hideOnSinglePage: true, showTotal: (total) => `共 ${total} 条` }} scroll={{ x: "max-content" }}
      {...props} sticky={props.sticky ?? { offsetHeader: DESIGN.header }}
      loading={props.loading ?? query?.isLoading} locale={{ ...props.locale, emptyText: empty }} />
  </div>;
}

type FilterBarProps = {
  search: string; onSearch: (value: string) => void; placeholder: string; count?: number;
  status?: string; onStatus?: (value: string) => void; options?: Array<{ value: string; label: string }>;
  onReset?: () => void; filtered?: boolean;
};

export function FilterBar({ search, onSearch, placeholder, count, status, onStatus, options, onReset, filtered }: FilterBarProps) {
  return <div className="af-work-filter">
    <Input value={search} prefix={<SearchOutlined />} placeholder={placeholder} aria-label={placeholder} allowClear
      onChange={(event) => onSearch(event.target.value)} />
    {options && <Select aria-label="筛选状态" value={status} onChange={onStatus} options={options} />}
    <div className="af-work-filter-meta" aria-live="polite">{count != null && <span>{count} 条{filtered ? "筛选结果" : "记录"}</span>}
      {filtered && <Button type="text" onClick={onReset}>清除筛选</Button>}</div>
  </div>;
}
