import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumber, formatUsd } from "../labels";
import { BRAND } from "../theme";
import { toRecharts, type ChartDatum } from "./types";
import { CHART } from "./chart-theme";

type HBarChartProps = { data: ChartDatum[]; format?: "number" | "usd"; maxBars?: number; height?: number };

function labelWidth(rows: ReturnType<typeof toRecharts>) {
  const widths = rows.map((row) => [...String(row.name)].reduce(
    (width, char) => width + (char.charCodeAt(0) > CHART.latinLimit ? CHART.wideWidth : CHART.latinWidth), CHART.labelPadding
  ));
  return Math.min(CHART.labelMax, Math.max(CHART.labelMin, ...widths));
}

export function HBarChart({ data, format = "number", maxBars = CHART.maxBars, height = CHART.horizontalHeight }: HBarChartProps) {
  const sorted = [...data].filter((row) => row.value > 0).sort((a, b) => b.value - a.value).slice(0, maxBars);
  const rows = toRecharts(sorted);
  if (!rows.length) return <div className="af-chart-empty">暂无费用或调用记录</div>;
  const chartHeight = Math.max(height, rows.length * CHART.rowHeight + CHART.axisSpace);
  const formatValue = (value: number) => format === "usd" ? formatUsd(value) : formatNumber(value);
  return <div className="af-chart-region" style={{ height: chartHeight }} role="img"
    aria-label={rows.map((row) => `${row.name}：${formatValue(row.value)}`).join("，")}>
    <ResponsiveContainer><BarChart data={rows} layout="vertical" margin={CHART.horizontalMargin}>
      <CartesianGrid horizontal={false} stroke={BRAND.line} />
      <XAxis type="number" tick={CHART.tick} axisLine={false} tickLine={false} allowDecimals={format === "usd"} />
      <YAxis type="category" dataKey="name" width={labelWidth(rows)} tick={CHART.tick} axisLine={false} tickLine={false} />
      <Tooltip formatter={(value) => [formatValue(Number(value ?? 0)), format === "usd" ? "费用" : "调用次数"]}
        contentStyle={CHART.tooltip} />
      <Bar dataKey="value" fill={BRAND.accent} barSize={CHART.barSize} isAnimationActive={false} />
    </BarChart></ResponsiveContainer>
  </div>;
}
