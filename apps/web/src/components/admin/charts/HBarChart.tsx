import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumber, formatUsd } from "../labels";
import { CHART_COLORS } from "../theme";
import { toRecharts, type ChartDatum } from "./types";

type HBarChartProps = {
  data: ChartDatum[];
  format?: "number" | "usd";
  maxBars?: number;
  height?: number;
};

export function HBarChart({
  data,
  format = "number",
  maxBars = 8,
  height = 260,
}: HBarChartProps) {
  const sorted = [...data]
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, maxBars);
  const rows = toRecharts(sorted);

  if (!rows.length) {
    return <div className="af-chart-empty">暂无数据</div>;
  }

  const h = Math.max(height, rows.length * 36 + 40);
  const fmt = (v: number) => (format === "usd" ? formatUsd(v) : formatNumber(v));

  return (
    <div style={{ width: "100%", height: h }}>
      <ResponsiveContainer>
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
          <XAxis type="number" tick={{ fontSize: 12, fill: "#8c8c8c" }} axisLine={false} />
          <YAxis
            type="category"
            dataKey="name"
            width={88}
            tick={{ fontSize: 12, fill: "#595959" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(v) => [fmt(Number(v ?? 0)), "数值"]}
            contentStyle={{ borderRadius: 8, border: "1px solid #f0f0f0" }}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={16}>
            {rows.map((r, i) => (
              <Cell key={r.key} fill={r.fill || CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
