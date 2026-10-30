export const HOURS_IN_DAY = 24;
export const QUIET_DISABLED = -1;
export const NIGHT_START = 22;
export const NIGHT_END = 8;
export const NOTIFICATION_CHANNELS = [{ value: "email", label: "邮件" }, { value: "sms", label: "短信" }];
export const NOTIFICATION_EVENTS = [
  { value: "mall.order.created", label: "订单创建" },
  { value: "mall.order.paid", label: "订单付款" },
  { value: "mall.order.shipped", label: "订单发货" },
  { value: "mall.order.delivered", label: "订单送达" },
  { value: "mall.order.completed", label: "订单完成" },
  { value: "mall.refund.settled", label: "退款到账" },
  { value: "mall.wallet.posted", label: "钱包变动" },
  { value: "mall.support.ticket_changed", label: "工单更新" },
];
export const QUIET_HOURS = [{ value: QUIET_DISABLED, label: "不设置" }, ...Array.from({ length: HOURS_IN_DAY },
  (_, hour) => ({ value: hour, label: `${String(hour).padStart(2, "0")}:00` }))];
export const INITIAL_PREFERENCE = { event_type: NOTIFICATION_EVENTS[0].value, channel: "email",
  enabled: true, quiet_start: QUIET_DISABLED, quiet_end: QUIET_DISABLED };

export function quietHoursError(start: number, end: number) {
  if ((start < 0) !== (end < 0)) return "请同时选择静默开始与结束时间，或均选择不设置。";
  if (start >= 0 && start === end) return "静默开始与结束时间不能相同。";
  return undefined;
}

export function quietLabel(row: Record<string, unknown>) {
  if (Number(row.quiet_start) < 0 || Number(row.quiet_end) < 0) return "无静默时段";
  const start = QUIET_HOURS.find((hour) => hour.value === row.quiet_start)?.label ?? "—";
  const end = QUIET_HOURS.find((hour) => hour.value === row.quiet_end)?.label ?? "—";
  return `${start}–${end} 静默 · ${String(row.timezone || "UTC")}`;
}
