import type { ReactNode } from "react";
import { Card, Statistic } from "antd";
import { formatNumber, formatRate, formatUsd } from "./labels";

type StatCardProps = {
  label: string;
  value: string | number | boolean | null | undefined;
  hint?: string;
  tone?: "default" | "brand" | "ok" | "warn" | "danger" | "info";
  format?: "number" | "usd" | "rate" | "raw";
  prefix?: ReactNode;
  /** Accepted for compatibility; metrics use labels rather than decorative icons. */
  icon?: ReactNode;
};

function renderValue(value: StatCardProps["value"], format: StatCardProps["format"]): string | number {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "string") return value;
  if (format === "usd") return formatUsd(value);
  if (format === "rate") return formatRate(value);
  if (format === "raw") return value;
  return formatNumber(value, Number.isInteger(value) ? 0 : 2);
}

export function StatCard({ label, value, hint, tone = "default", format = "number", prefix }: StatCardProps) {
  return <Card className={`af-stat-card af-tone-${tone}`} variant="borderless">
    <div className="af-stat-body">
      <Statistic title={label} value={renderValue(value, format)} prefix={prefix} />
      {hint && <p className="af-stat-hint">{hint}</p>}
    </div>
  </Card>;
}
