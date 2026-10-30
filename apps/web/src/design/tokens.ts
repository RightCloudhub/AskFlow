/** Shared by ConfigProvider, custom surfaces and charts. */
export const BRAND = {
  primary: "#243b43",
  primaryHover: "#36525a",
  primaryActive: "#172d34",
  primarySoft: "#e9eef0",
  accent: "#23756e",
  ink: "#202e35",
  ink2: "#4d5e66",
  muted: "#64727a",
  line: "#e5eaed",
  bgLayout: "#f5f7f8",
  frame: "#eef2f3",
  surface: "#ffffff",
  surfaceAlt: "#f8fafb",
  control: "#ccd5d9",
  accentSoft: "#edf5f3",
  success: "#28664b",
  successSoft: "#eaf4ed",
  warning: "#855c1d",
  warningSoft: "#faf3e8",
  danger: "#a33e48",
  dangerSoft: "#fbefef",
};

export const DESIGN = {
  font: '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  mono: 'ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace',
  radius: { panel: 16, control: 8, chip: 4, pill: 999 },
  type: { meta: 12, body: 14, reading: 16, section: 18, title: 26, figure: 32 },
  space: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, section: 40 },
  sidebar: 256,
  rail: 280,
  header: 64,
  controlHeight: 38,
  controlHeightLarge: 44,
  floatingShadow: "0 12px 36px rgb(32 46 53 / 12%)",
  focusRing: "0 0 0 3px rgb(35 117 110 / 16%)",
  duration: "160ms",
  motionDuration: "0.16s",
};

export const CHART_COLORS = [BRAND.accent, "#849a9f", "#b4c1c5", "#d9e1e4"];
