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
  const fmt = (v: number) =>
    format === "usd" ? formatUsd(v) : formatNumber(v);

  // Fit the category axis to the longest label (CJK glyphs ≈ 12px, latin ≈ 7px).
  const labelWidth = Math.min(
    160,
    Math.max(
      56,
      ...rows.map((r) =>
        [...String(r.name)].reduce(
          (w, ch) => w + (ch.charCodeAt(0) > 255 ? 12 : 7),
          12,
        ),
      ),
    ),
  );

  return (
    <div style={{ width: "100%", height: h }}>
      <ResponsiveContainer>
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
            stroke="#eceff5"
          />
          <XAxis
            type="number"
            tick={{ fontSize: 12, fill: "#8a93a6" }}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={labelWidth}
            tick={{ fontSize: 12, fill: "#4b5567" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(v) => [fmt(Number(v ?? 0)), "数值"]}
            contentStyle={{ borderRadius: 8, border: "1px solid #eceff5" }}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={16}>
            {rows.map((r, i) => (
              <Cell
                key={r.key}
                fill={r.fill || CHART_COLORS[i % CHART_COLORS.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
