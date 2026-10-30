import type { ThemeConfig } from "antd";

/**
 * AskFlow design tokens — clean enterprise SaaS on top of Ant Design.
 * Neutral chrome, clear reading hierarchy and one teal hue for data.
 * CSS variables in styles/global.css mirror these values for custom markup.
 */
export const BRAND = {
  primary: "#1c2529",
  primaryHover: "#344349",
  primaryActive: "#171d20",
  primarySoft: "#e8edef",
  accent: "#1b6c80",
  ink: "#171d20",
  ink2: "#4d585d",
  muted: "#606c72",
  line: "#e5eaec",
  bgLayout: "#f3f6f7",
};

export const adminTheme: ThemeConfig = {
  token: {
    colorPrimary: BRAND.primary,
    colorInfo: BRAND.accent,
    colorSuccess: "#24734b",
    colorWarning: "#8a5a12",
    colorError: "#b02a32",
    colorLink: BRAND.accent,
    colorTextBase: BRAND.ink,
    colorTextSecondary: BRAND.ink2,
    colorTextTertiary: BRAND.muted,
    colorBorder: "#c5ced2",
    colorBorderSecondary: BRAND.line,
    colorBgLayout: BRAND.bgLayout,
    colorBgContainer: "#ffffff",
    colorFillAlter: "#f7f9f9",
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    fontSize: 14,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", "Helvetica Neue", Arial, sans-serif',
    controlHeight: 36,
    boxShadow: "none",
    boxShadowSecondary:
      "0 6px 24px rgba(29, 36, 51, 0.10), 0 2px 6px rgba(29, 36, 51, 0.06)",
    motionDurationMid: "0.18s",
  },
  components: {
    Layout: {
      siderBg: BRAND.bgLayout,
      headerBg: BRAND.bgLayout,
      headerHeight: 48,
      headerPadding: "0 24px",
      bodyBg: BRAND.bgLayout,
      lightSiderBg: BRAND.bgLayout,
      triggerBg: "#ffffff",
      triggerColor: BRAND.ink2,
    },
    Menu: {
      itemBg: "transparent",
      subMenuItemBg: "transparent",
      itemHeight: 38,
      itemMarginInline: 8,
      itemMarginBlock: 2,
      itemBorderRadius: 8,
      itemColor: BRAND.ink2,
      itemHoverBg: "#e8edef",
      itemSelectedBg: BRAND.primarySoft,
      itemSelectedColor: BRAND.primary,
      groupTitleColor: BRAND.muted,
      groupTitleFontSize: 12,
      iconSize: 15,
      collapsedIconSize: 16,
      activeBarBorderWidth: 0,
    },
    Card: {
      headerFontSize: 15,
      headerHeight: 52,
      paddingLG: 20,
    },
    Table: {
      headerBg: "#ffffff",
      headerColor: BRAND.ink2,
      headerSplitColor: "transparent",
      rowHoverBg: "#f7f9f9",
      cellPaddingBlock: 12,
      borderColor: BRAND.line,
    },
    Statistic: {
      titleFontSize: 13,
      contentFontSize: 26,
    },
    Button: {
      fontWeight: 500,
      primaryShadow: "none",
    },
    Tag: {
      defaultBg: "#e8edef",
    },
    Drawer: {
      paddingLG: 20,
    },
    Tabs: {
      horizontalItemPadding: "10px 0",
    },
  },
};

export const CHART_COLORS = [
  "#1b6c80",
  "#6d838c",
  "#a0b0b6",
  "#c8d3d7",
];
