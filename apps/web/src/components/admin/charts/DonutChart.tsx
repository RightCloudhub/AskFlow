import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { CHART_COLORS } from "../theme";
import { toRecharts, type ChartDatum } from "./types";
import { CHART } from "./chart-theme";

type DonutChartProps = { data: ChartDatum[]; centerLabel?: string; centerValue?: string; height?: number };

function DonutLegend({ rows }: { rows: ReturnType<typeof toRecharts> }) {
  return <ul className="af-chart-legend compact">{rows.map((row, index) => <li key={row.key}>
    <span className="af-swatch" style={{ background: row.fill || CHART_COLORS[index % CHART_COLORS.length] }} />
    <span className="af-legend-label">{row.name}</span><strong>{row.value.toLocaleString("zh-CN")}</strong>
  </li>)}</ul>;
}

export function DonutChart({ data, centerLabel, centerValue, height = CHART.height }: DonutChartProps) {
  const rows = toRecharts(data.filter((row) => row.value > 0));
  if (!rows.length) return <div className="af-chart-empty">暂无分布数据</div>;
  return <div className="af-donut">
    <div style={{ width: "100%", height, position: "relative" }} role="img"
      aria-label={rows.map((row) => `${row.name}：${row.value}`).join("，")}>
      <ResponsiveContainer><PieChart><Pie data={rows} dataKey="value" nameKey="name" cx="50%" cy="50%"
        innerRadius={CHART.ringInner} outerRadius={CHART.ringOuter} paddingAngle={rows.length > 1 ? 2 : 0}
        stroke="none" isAnimationActive={false}>
        {rows.map((row, index) => <Cell key={row.key} fill={row.fill || CHART_COLORS[index % CHART_COLORS.length]} />)}
      </Pie><Tooltip formatter={(value, name) => [Number(value ?? 0).toLocaleString("zh-CN"), String(name ?? "")]}
        contentStyle={CHART.tooltip} /></PieChart></ResponsiveContainer>
      {(centerValue || centerLabel) && <div className="af-donut-center">
        {centerValue && <strong>{centerValue}</strong>}{centerLabel && <span>{centerLabel}</span>}
      </div>}
    </div>
    <DonutLegend rows={rows} />
  </div>;
}
