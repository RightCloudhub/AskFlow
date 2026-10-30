import { Alert, Button, Form, List, Select, Switch } from "antd";
import { useCallback, useState } from "react";
import { mall, write } from "./client";
import { Feedback, useLoad, type Page, type Row } from "./shared";

const HOURS_IN_DAY = 24;
const QUIET_DISABLED = -1;
const CHANNELS = [{ value: "email", label: "邮件" }, { value: "sms", label: "短信" }];
const EVENTS = [
  { value: "mall.order.paid", label: "订单付款" }, { value: "mall.order.shipped", label: "订单发货" },
  { value: "mall.refund.settled", label: "退款到账" }, { value: "mall.wallet.posted", label: "钱包变动" },
  { value: "mall.support.ticket_changed", label: "工单更新" },
];
const HOURS = [{ value: QUIET_DISABLED, label: "不设置静默时段" }, ...Array.from({ length: HOURS_IN_DAY },
  (_, hour) => ({ value: hour, label: `${String(hour).padStart(2, "0")}:00` }))];

function PreferenceRows({ rows }: { rows: Row[] }) {
  return <List className="af-mall-feed" dataSource={rows} locale={{ emptyText: "尚未设置通知偏好。" }} renderItem={(row) => <List.Item>
    <div className="af-mall-message"><strong>{EVENTS.find((event) => event.value === row.event_type)?.label ?? String(row.event_type)}</strong>
      <p>{CHANNELS.find((channel) => channel.value === row.channel)?.label ?? String(row.channel)}</p></div>
    <span>{row.enabled ? "接收" : "关闭"}</span>
  </List.Item>} />;
}

export function NotificationPreferences() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const query = useLoad(useCallback(() => mall<Page<Row>>("/notify/preferences"), []));
  async function save(values: Row) {
    setBusy(true); setSaved(false);
    try {
      await write("/notify/preferences", { ...values, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone }, { method: "PUT" });
      setError(""); setSaved(true); await query.reload();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "保存失败"); }
    finally { setBusy(false); }
  }
  return <><Feedback error={error || query.error} loading={query.loading} /><PreferenceRows rows={query.data?.items ?? []} />
    <Form className="af-mall-form" layout="vertical" onFinish={save} initialValues={{
      event_type: EVENTS[0].value, channel: "email", enabled: true, quiet_start: QUIET_DISABLED, quiet_end: QUIET_DISABLED,
    }}>
      <Form.Item name="event_type" label="通知事件"><Select options={EVENTS} /></Form.Item>
      <Form.Item name="channel" label="通知方式"><Select options={CHANNELS} /></Form.Item>
      <Form.Item name="enabled" label="接收此类通知" valuePropName="checked"><Switch /></Form.Item>
      <Form.Item name="quiet_start" label="静默开始时间"><Select options={HOURS} /></Form.Item>
      <Form.Item name="quiet_end" label="静默结束时间"><Select options={HOURS} /></Form.Item>
      <Button type="primary" htmlType="submit" loading={busy}>保存通知偏好</Button>
      {saved && <Alert type="success" title="通知偏好已保存" role="status" />}
    </Form>
  </>;
}
