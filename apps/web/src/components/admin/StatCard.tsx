import type { ReactNode } from "react";
import { Card, Statistic } from "antd";
import {
  AlertOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { formatNumber, formatRate, formatUsd } from "./labels";

type StatTone = "default" | "brand" | "ok" | "warn" | "danger" | "info";

type StatCardProps = {
  label: string;
  value: string | number | boolean | null | undefined;
  hint?: string;
  tone?: StatTone;
  format?: "number" | "usd" | "rate" | "raw";
  prefix?: ReactNode;
  /** Icon shown in the tinted tile; defaults to a tone icon. */
  icon?: ReactNode;
};

function renderValue(
  value: string | number | boolean | null | undefined,
  format: StatCardProps["format"],
): string | number {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "string") return value;
  if (format === "usd") return formatUsd(value);
  if (format === "rate") return formatRate(value);
  if (format === "raw") return value;
  return formatNumber(value, Number.isInteger(value) ? 0 : 2);
}

const TONE_ICON: Record<StatTone, ReactNode> = {
  default: <DashboardOutlined />,
  brand: <DashboardOutlined />,
  ok: <CheckCircleOutlined />,
  warn: <WarningOutlined />,
  danger: <AlertOutlined />,
  info: <InfoCircleOutlined />,
};

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  format = "number",
  prefix,
  icon,
}: StatCardProps) {
  return (
    <Card className={`af-stat-card af-tone-${tone}`} variant="borderless">
      <div className="af-stat-body">
        <Statistic
          title={label}
          value={renderValue(value, format) as string | number}
          prefix={prefix}
          suffix={
            hint ? <span className="af-stat-suffix">{hint}</span> : undefined
          }
        />
        <span className="af-stat-icon" aria-hidden>
          {icon ?? TONE_ICON[tone]}
        </span>
      </div>
    </Card>
  );
}
