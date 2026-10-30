import { Button, Form, List, Select, Switch, Tag } from "antd";
import { useCallback } from "react";
import { mall, write } from "./client";
import { useLoad, type Page, type Row } from "./shared";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";

const HOURS_IN_DAY = 24;
const QUIET_DISABLED = -1;
const CHANNELS = [{ value: "email", label: "邮件" }, { value: "sms", label: "短信" }];
const EVENTS = [
  { value: "mall.order.paid", label: "订单付款" }, { value: "mall.order.shipped", label: "订单发货" },
  { value: "mall.refund.settled", label: "退款到账" }, { value: "mall.wallet.posted", label: "钱包变动" },
  { value: "mall.support.ticket_changed", label: "工单更新" },
];
const HOURS = [{ value: QUIET_DISABLED, label: "不设置" }, ...Array.from({ length: HOURS_IN_DAY },
  (_, hour) => ({ value: hour, label: `${String(hour).padStart(2, "0")}:00` }))];
const INITIAL = { event_type: EVENTS[0].value, channel: "email", enabled: true, quiet_start: QUIET_DISABLED, quiet_end: QUIET_DISABLED };

function quietLabel(row: Row) {
  if (Number(row.quiet_start) < 0 || Number(row.quiet_end) < 0) return "无静默时段";
  const start = HOURS.find((hour) => hour.value === row.quiet_start)?.label ?? "—";
  const end = HOURS.find((hour) => hour.value === row.quiet_end)?.label ?? "—";
  return `${start}–${end} 静默 · ${String(row.timezone || "UTC")}`;
}

function PreferenceRows({ rows, edit }: { rows: Row[]; edit: (row: Row) => void }) {
  return <List className="af-mall-feed" dataSource={rows} locale={{ emptyText: "尚未设置通知偏好，可在下方选择事件与接收方式。" }} renderItem={(row) => <List.Item>
    <div className="af-mall-message"><strong>{EVENTS.find((event) => event.value === row.event_type)?.label ?? String(row.event_type)}</strong>
      <p>{CHANNELS.find((channel) => channel.value === row.channel)?.label ?? String(row.channel)} · {quietLabel(row)}</p></div>
    <div className="af-work-actions"><Tag>{row.enabled ? "接收" : "关闭"}</Tag><Button type="text" onClick={() => edit(row)}>编辑</Button></div>
  </List.Item>} />;
}

export function NotificationPreferences() {
  const [form] = Form.useForm();
  const paging = useCursor();
  const feedback = useActionFeedback();
  const query = useLoad(useCallback(() => mall<Page<Row>>(`/notify/preferences?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]));
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  async function save(values: Row) {
    await feedback.run(async () => {
      const start = Number(values.quiet_start), end = Number(values.quiet_end);
      if ((start < 0) !== (end < 0)) throw new Error("请同时选择静默开始与结束时间，或均选择不设置。");
      if (start >= 0 && start === end) throw new Error("静默开始与结束时间不能相同。");
      await write("/notify/preferences", { ...values, timezone }, { method: "PUT" }); await query.reload();
    }, "通知偏好已保存。");
  }
  return <div className="af-security-stack"><div className="af-security-heading"><h3>当前通知偏好</h3><QueryRefresh query={query} /></div>
    <MallQuery query={query}><PreferenceRows rows={query.data?.items ?? []} edit={(row) => {
      form.setFieldsValue(row); feedback.clear(); form.scrollToField("event_type", { focus: true });
    }} /></MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
    <Form form={form} className="af-mall-form" layout="vertical" onFinish={save} initialValues={INITIAL}
      disabled={feedback.busy} onValuesChange={feedback.clear} scrollToFirstError={{ focus: true }}>
      <Form.Item name="event_type" label="通知事件" rules={[{ required: true, message: "请选择通知事件。" }]}><Select options={EVENTS} /></Form.Item>
      <Form.Item name="channel" label="通知方式" rules={[{ required: true, message: "请选择通知方式。" }]}><Select options={CHANNELS} /></Form.Item>
      <Form.Item name="enabled" label="接收此类通知" valuePropName="checked"><Switch checkedChildren="接收" unCheckedChildren="关闭" /></Form.Item>
      <div className="af-quiet-hours"><Form.Item name="quiet_start" label="静默开始时间"><Select options={HOURS} /></Form.Item>
        <Form.Item name="quiet_end" label="静默结束时间"><Select options={HOURS} /></Form.Item></div>
      <p className="af-mall-note">时间使用 {timezone}。静默时段可跨午夜；站内消息仍会保留。</p>
      <div className="af-mall-form-actions"><Button type="primary" htmlType="submit" loading={feedback.busy}>保存通知偏好</Button><ActionFeedback state={feedback} /></div>
    </Form>
  </div>;
}
