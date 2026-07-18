import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { CHART_COLORS } from "../theme";
import { toRecharts, type ChartDatum } from "./types";

type DonutChartProps = {
  data: ChartDatum[];
  centerLabel?: string;
  centerValue?: string;
  height?: number;
};

export function DonutChart({
  data,
  centerLabel,
  centerValue,
  height = 260,
}: DonutChartProps) {
  const rows = toRecharts(data.filter((d) => d.value > 0));
  if (!rows.length) {
    return <div className="af-chart-empty">暂无数据</div>;
  }

  return (
    <div style={{ width: "100%", height, position: "relative" }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={rows}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius="58%"
            outerRadius="80%"
            paddingAngle={2}
          >
            {rows.map((r, i) => (
              <Cell key={r.key} fill={r.fill || CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v, name) => [
              Number(v ?? 0).toLocaleString("zh-CN"),
              String(name ?? ""),
            ]}
            contentStyle={{ borderRadius: 8, border: "1px solid #f0f0f0" }}
          />
        </PieChart>
      </ResponsiveContainer>
      {(centerValue || centerLabel) && (
        <div className="af-donut-center">
          {centerValue ? <strong>{centerValue}</strong> : null}
          {centerLabel ? <span>{centerLabel}</span> : null}
        </div>
      )}
      <ul className="af-chart-legend compact">
        {rows.map((r, i) => (
          <li key={r.key}>
            <span
              className="af-swatch"
              style={{ background: r.fill || CHART_COLORS[i % CHART_COLORS.length] }}
            />
            <span className="af-legend-label">{r.name}</span>
            <strong>{r.value.toLocaleString("zh-CN")}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}
