import { Button, List, Tag } from "antd";
import { useCallback, useState } from "react";
import { mall } from "./client";
import { useLoad, type Page, type Row } from "./shared";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { NotificationPreferenceForm } from "./NotificationPreferenceForm";
import { NOTIFICATION_CHANNELS as CHANNELS, NOTIFICATION_EVENTS as EVENTS, quietLabel } from "./notification-options";

function PreferenceRows({ rows, edit }: { rows: Row[]; edit: (row: Row) => void }) {
  return <List className="af-mall-feed" dataSource={rows} locale={{ emptyText: "尚未设置通知偏好，可在下方选择事件与接收方式。" }} renderItem={(row) => <List.Item>
    <div className="af-mall-message"><strong>{EVENTS.find((event) => event.value === row.event_type)?.label ?? String(row.event_type)}</strong>
      <p>{CHANNELS.find((channel) => channel.value === row.channel)?.label ?? String(row.channel)} · {quietLabel(row)}</p></div>
    <div className="af-work-actions"><Tag>{row.enabled ? "接收" : "关闭"}</Tag><Button type="text" onClick={() => edit(row)}>编辑</Button></div>
  </List.Item>} />;
}

export function NotificationPreferences() {
  const [editing, setEditing] = useState<Row>();
  const [revision, setRevision] = useState(0);
  const paging = useCursor();
  const query = useLoad(useCallback(() => mall<Page<Row>>(`/notify/preferences?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]));
  return <div className="af-security-stack"><div className="af-security-heading"><h3>当前通知偏好</h3><QueryRefresh query={query} /></div>
    <MallQuery query={query}><PreferenceRows rows={query.data?.items ?? []} edit={(row) => {
      setEditing(row); setRevision((value) => value + 1);
    }} /></MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
    <NotificationPreferenceForm key={revision} initial={editing} reload={query.reload} />
  </div>;
}
