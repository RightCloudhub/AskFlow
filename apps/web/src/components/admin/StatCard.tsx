import { Card, Statistic } from "antd";
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  DashboardOutlined,
} from "@ant-design/icons";
import { formatNumber, formatRate, formatUsd } from "./labels";

type StatTone = "default" | "brand" | "ok" | "warn" | "danger" | "info";

type StatCardProps = {
  label: string;
  value: string | number | boolean | null | undefined;
  hint?: string;
  tone?: StatTone;
  format?: "number" | "usd" | "rate" | "raw";
  prefix?: React.ReactNode;
};

const TONE_COLOR: Record<StatTone, string | undefined> = {
  default: undefined,
  brand: "#1677ff",
  ok: "#52c41a",
  warn: "#faad14",
  danger: "#ff4d4f",
  info: "#1677ff",
};

function renderValue(
  value: string | number | boolean | null | undefined,
  format: StatCardProps["format"]
): string | number {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "string") return value;
  if (format === "usd") return formatUsd(value);
  if (format === "rate") return formatRate(value);
  if (format === "raw") return value;
  return formatNumber(value, Number.isInteger(value) ? 0 : 2);
}

function toneIcon(tone: StatTone) {
  if (tone === "ok") return <ArrowUpOutlined />;
  if (tone === "danger" || tone === "warn") return <ArrowDownOutlined />;
  return <DashboardOutlined />;
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  format = "number",
  prefix,
}: StatCardProps) {
  return (
    <Card size="small" className="af-stat-card" bordered hoverable>
      <Statistic
        title={label}
        value={renderValue(value, format) as string | number}
        valueStyle={{ color: TONE_COLOR[tone], fontWeight: 600 }}
        prefix={prefix ?? toneIcon(tone)}
        suffix={hint ? <span className="af-stat-suffix">{hint}</span> : undefined}
      />
    </Card>
  );
}
