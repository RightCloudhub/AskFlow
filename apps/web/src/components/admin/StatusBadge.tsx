import { Tag } from "antd";
import { labelStatus, statusTone } from "./labels";

type StatusBadgeProps = {
  value: string | null | undefined;
  label?: string;
};

const TONE_COLOR: Record<string, string> = {
  ok: "success",
  warn: "warning",
  danger: "error",
  info: "processing",
  neutral: "default",
};

export function StatusBadge({ value, label }: StatusBadgeProps) {
  const tone = statusTone(value);
  return (
    <Tag color={TONE_COLOR[tone] ?? "default"}>{label ?? labelStatus(value)}</Tag>
  );
}
