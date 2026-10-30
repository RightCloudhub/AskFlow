import type { CSSProperties } from "react";
import { formatNumber, formatUsd } from "../labels";
import { type ChartDatum } from "./types";
import { CHART } from "./chart-theme";

type HBarChartProps = {
  data: ChartDatum[]; format?: "number" | "usd"; maxBars?: number; height?: number; emptyText?: string;
};
const PERCENT_SCALE = 100;

export function HBarChart({ data, format = "number", maxBars = CHART.maxBars, height = CHART.horizontalHeight,
  emptyText = "当前没有这类记录" }: HBarChartProps) {
  const rows = [...data].filter((row) => Number.isFinite(row.value) && row.value >= 0)
    .sort((a, b) => b.value - a.value).slice(0, maxBars);
  if (!rows.length) return <div className="af-chart-empty">{emptyText}</div>;
  const maximum = Math.max(0, ...rows.map((row) => row.value));
  const value = (amount: number) => format === "usd" ? formatUsd(amount) : formatNumber(amount);
  return <div className="af-bar-list" style={{ minHeight: Math.min(height, rows.length * CHART.rowHeight) }}
    role="img" aria-label={rows.map((row) => `${row.label}：${value(row.value)}`).join("，")}>
    {rows.map((row) => <div key={row.key} className="af-bar-list-row"
      style={{ "--bar-share": `${maximum ? row.value / maximum * PERCENT_SCALE : 0}%` } as CSSProperties}>
      <span>{row.label}</span><strong>{value(row.value)}</strong><div className="af-bar-list-track"><i /></div>
    </div>)}
  </div>;
}
