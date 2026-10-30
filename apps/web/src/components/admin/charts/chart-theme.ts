import { BRAND } from "../theme";

export const CHART = {
  height: 220,
  horizontalHeight: 180,
  maxBars: 8,
  rowHeight: 36,
  axisSpace: 40,
  labelMin: 64,
  labelMax: 168,
  latinWidth: 7,
  wideWidth: 12,
  latinLimit: 255,
  labelPadding: 12,
  barSize: 12,
  maxBarSize: 36,
  axisWidth: 40,
  ringInner: "74%",
  ringOuter: "80%",
  tick: { fontSize: 12, fill: BRAND.muted },
  margin: { top: 8, right: 8, left: 0, bottom: 0 },
  horizontalMargin: { top: 4, right: 24, left: 0, bottom: 4 },
  tooltip: { borderRadius: 6, border: `1px solid ${BRAND.line}`, boxShadow: "none" },
};
