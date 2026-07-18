export type ChartDatum = {
  key: string;
  label: string;
  value: number;
  color?: string;
};

export { CHART_COLORS as CHART_PALETTE } from "../theme";

export function toRecharts(data: ChartDatum[]) {
  return data.map((d) => ({
    name: d.label,
    value: d.value,
    key: d.key,
    fill: d.color,
  }));
}
