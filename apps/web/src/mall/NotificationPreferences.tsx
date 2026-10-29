import { Form, Button, InputNumber, List, Select, Switch } from "antd";
import { useCallback, useState } from "react";
import { mall, write } from "./client";
import { Feedback, useLoad, type Page, type Row } from "./shared";

const HOURS_IN_DAY = 24;

const EVENTS = [
  { value: "mall.order.paid", label: "订单付款" }, { value: "mall.order.shipped", label: "订单发货" },
  { value: "mall.refund.settled", label: "退款到账" }, { value: "mall.wallet.posted", label: "钱包变动" },
  { value: "mall.support.ticket_changed", label: "工单更新" },
];

export function NotificationPreferences() {
  const [error, setError] = useState("");
  const query = useLoad(useCallback(() => mall<Page<Row>>("/notify/preferences"), []));
  async function save(values: Row) {
    try {
      await write("/notify/preferences", { ...values, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone }, { method: "PUT" });
      setError("");
      await query.reload();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "保存失败"); }
  }
  return <><List dataSource={query.data?.items} renderItem={(row) => <List.Item>
    {String(row.event_type)} · {String(row.channel)} · {row.enabled ? "接收" : "关闭"}
  </List.Item>} /><Form layout="vertical" onFinish={save} initialValues={{ event_type: EVENTS[0].value, channel: "email", enabled: true, quiet_start: -1, quiet_end: -1 }}>
    <Form.Item name="event_type" label="通知事件"><Select options={EVENTS} /></Form.Item>
    <Form.Item name="channel" label="通知方式"><Select options={[
      { value: "email", label: "邮件" }, { value: "sms", label: "短信" },
    ]} /></Form.Item>
    <Form.Item name="enabled" label="接收此类通知" valuePropName="checked"><Switch /></Form.Item>
    <Form.Item name="quiet_start" label="静默开始时间（小时，-1 为关闭）"><InputNumber min={-1} max={HOURS_IN_DAY - 1} precision={0} /></Form.Item>
    <Form.Item name="quiet_end" label="静默结束时间（小时，-1 为关闭）"><InputNumber min={-1} max={HOURS_IN_DAY - 1} precision={0} /></Form.Item>
    <Button htmlType="submit">保存通知偏好</Button><Feedback error={error || query.error} />
  </Form></>;
}
