import { Bar, BarChart as RBarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BRAND } from "../theme";
import { toRecharts, type ChartDatum } from "./types";
import { CHART } from "./chart-theme";

type BarChartProps = { data: ChartDatum[]; height?: number; unit?: string };

export function BarChart({ data, height = CHART.height, unit = "" }: BarChartProps) {
  const rows = toRecharts(data.filter((row) => row.value >= 0));
  if (!rows.length) return <div className="af-chart-empty">暂无工作量数据</div>;
  return <div className="af-chart-region" style={{ height }} role="img"
    aria-label={rows.map((row) => `${row.name}：${row.value}${unit}`).join("，")}>
    <ResponsiveContainer><RBarChart data={rows} margin={CHART.margin}>
      <CartesianGrid vertical={false} stroke={BRAND.line} />
      <XAxis dataKey="name" tick={CHART.tick} axisLine={false} tickLine={false} />
      <YAxis tick={CHART.tick} axisLine={false} tickLine={false} width={CHART.axisWidth} allowDecimals={false} />
      <Tooltip formatter={(value) => [`${Number(value ?? 0).toLocaleString("zh-CN")}${unit}`, "数量"]}
        contentStyle={CHART.tooltip} />
      <Bar dataKey="value" fill={BRAND.accent} maxBarSize={CHART.maxBarSize} isAnimationActive={false} />
    </RBarChart></ResponsiveContainer>
  </div>;
}
