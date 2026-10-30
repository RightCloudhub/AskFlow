import { Button, Form, Select, Switch } from "antd";
import type { FormInstance } from "antd";
import { GuidedForm } from "../components/common/GuidedForm";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { write } from "./client";
import { INITIAL_PREFERENCE, NIGHT_START, NIGHT_END, NOTIFICATION_CHANNELS, NOTIFICATION_EVENTS,
  QUIET_DISABLED, QUIET_HOURS, quietHoursError, quietLabel } from "./notification-options";

type Row = Record<string, unknown>;

function QuietHours({ form, timezone }: { form: FormInstance; timezone: string }) {
  const validation = { validator: async () => {
    const error = quietHoursError(Number(form.getFieldValue("quiet_start")), Number(form.getFieldValue("quiet_end")));
    if (error) throw new Error(error);
  } };
  function preset(start: number, end: number) {
    form.setFieldsValue({ quiet_start: start, quiet_end: end });
    void form.validateFields(["quiet_end"]).catch(() => undefined);
  }
  return <><div className="af-work-actions">
    <Button onClick={() => preset(NIGHT_START, NIGHT_END)}>夜间免打扰</Button>
    <Button onClick={() => preset(QUIET_DISABLED, QUIET_DISABLED)}>全天接收</Button>
  </div><div className="af-quiet-hours">
    <Form.Item name="quiet_start" label="静默开始时间"><Select options={QUIET_HOURS} /></Form.Item>
    <Form.Item name="quiet_end" label="静默结束时间" dependencies={["quiet_start"]} rules={[validation]}>
      <Select options={QUIET_HOURS} /></Form.Item>
  </div><p className="af-mall-note">时间使用 {timezone}。静默时段可跨午夜；站内消息仍会保留。</p></>;
}

function PreferenceReview({ values }: { values: Row }) {
  return <dl><div><dt>通知事件</dt><dd>{NOTIFICATION_EVENTS.find((event) => event.value === values.event_type)?.label ?? String(values.event_type)}</dd></div>
    <div><dt>接收方式</dt><dd>{values.enabled ? NOTIFICATION_CHANNELS.find((channel) => channel.value === values.channel)?.label : "关闭此类通知"}</dd></div>
    <div><dt>接收时间</dt><dd>{quietLabel(values)}</dd></div></dl>;
}

export function NotificationPreferenceForm({ initial, reload, onBusyChange }: {
  initial?: Row; reload: () => Promise<void>; onBusyChange?: (busy: boolean) => void;
}) {
  const [form] = Form.useForm();
  const feedback = useActionFeedback();
  const timezone = String(initial?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone);
  async function save(values: Row) {
    return feedback.run(async () => {
      const { event_type, channel, enabled, quiet_start, quiet_end } = values;
      await write("/notify/preferences", { event_type, channel, enabled, quiet_start, quiet_end, timezone }, { method: "PUT" });
      await reload();
    }, "通知偏好已保存。");
  }
  return <GuidedForm form={form} initialValues={{ ...INITIAL_PREFERENCE, ...initial }} onFinish={save}
    onBusyChange={onBusyChange}
    submitLabel="保存通知偏好" onValuesChange={feedback.clear} feedback={<ActionFeedback state={feedback} />}
    steps={[
      { title: "接收内容", fields: ["event_type", "channel", "enabled"], content: <>
        <Form.Item name="event_type" label="通知事件" rules={[{ required: true, message: "请选择通知事件。" }]}><Select options={NOTIFICATION_EVENTS} /></Form.Item>
        <Form.Item name="channel" label="通知方式" rules={[{ required: true, message: "请选择通知方式。" }]}><Select options={NOTIFICATION_CHANNELS} /></Form.Item>
        <Form.Item name="enabled" label="接收此类通知" valuePropName="checked"><Switch checkedChildren="接收" unCheckedChildren="关闭" /></Form.Item>
      </> },
      { title: "接收时间", fields: ["quiet_start", "quiet_end"], content: <QuietHours form={form} timezone={timezone} /> },
    ]} review={(values) => <PreferenceReview values={{ ...values, timezone }} />} />;
}
