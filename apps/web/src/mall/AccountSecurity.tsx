import { useCallback } from "react";
import { Button, List, Popconfirm, Tag } from "antd";
import { mall, write } from "./client";
import { useLoad, type Page } from "./shared";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { formatDate } from "./presentation";
import { MfaSettings, securitySignOut as signedOut } from "./MfaSettings";

type Device = { id: string; device: string; user_agent: string; revoked_at: string | null; last_active?: string };
function DeviceSessions() {
  const paging = useCursor();
  const loader = useCallback(() => mall<Page<Device>>(`/account/sessions?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]);
  const query = useLoad(loader);
  const feedback = useActionFeedback();
  return <section className="af-security-block"><div className="af-security-heading"><h3>登录设备</h3><QueryRefresh query={query} /></div>
    <ActionFeedback state={feedback} /><MallQuery query={query}>
      <List className="af-device-list" dataSource={query.data?.items} locale={{ emptyText: "暂无登录设备。" }} renderItem={(device) => <List.Item>
        <div className="af-device-identity"><strong>{device.user_agent || device.device || "登录设备"}</strong>
          <span>最近活跃 {formatDate(device.last_active)}</span><span className="af-device-id">设备标识 {device.device || device.id}</span></div>
        {device.revoked_at ? <Tag>已下线</Tag> : <Popconfirm title="让此设备下线？" description="此设备需要重新登录；若为本机，当前会话也将结束。"
          okText="确认下线" cancelText="保留" onConfirm={() => feedback.run(async () => {
            await write(`/account/sessions/${device.id}`, {}, { method: "DELETE" }); await query.reload();
          }, "设备已下线。") }><Button type="text" disabled={feedback.busy}>下线</Button></Popconfirm>}
      </List.Item>} />
    </MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
    <Popconfirm title="退出所有登录设备？" description="包括当前设备，操作后需要重新登录。" okText="退出全部" cancelText="保留"
      onConfirm={() => feedback.run(async () => { await write("/account/sessions/revoke-all", {}); signedOut(); })}>
      <Button danger loading={feedback.busy}>退出全部设备</Button>
    </Popconfirm>
  </section>;
}

export function Security({ mfaEnabled }: { mfaEnabled: boolean }) {
  return <div className="af-security-stack"><MfaSettings enabled={mfaEnabled} /><DeviceSessions /></div>;
}
