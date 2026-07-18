import {
  Bar,
  BarChart as RBarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART_COLORS } from "../theme";
import { toRecharts, type ChartDatum } from "./types";

type BarChartProps = {
  data: ChartDatum[];
  height?: number;
  unit?: string;
};

export function BarChart({ data, height = 260, unit = "" }: BarChartProps) {
  const rows = toRecharts(data.filter((d) => d.value >= 0));
  if (!rows.length) {
    return <div className="af-chart-empty">暂无数据</div>;
  }

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <RBarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: "#8c8c8c" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "#8c8c8c" }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            formatter={(v) => [
              `${Number(v ?? 0).toLocaleString("zh-CN")}${unit}`,
              "数值",
            ]}
            contentStyle={{ borderRadius: 8, border: "1px solid #f0f0f0" }}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={48}>
            {rows.map((r, i) => (
              <Cell key={r.key} fill={r.fill || CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Bar>
        </RBarChart>
      </ResponsiveContainer>
    </div>
  );
}
