import type { ThemeConfig } from "antd";

/**
 * AskFlow design tokens — clean enterprise SaaS on top of Ant Design.
 * Light surfaces, generous whitespace, one brand blue, soft neutral borders.
 * CSS variables in styles/global.css mirror these values for custom markup.
 */
export const BRAND = {
  primary: "#2f6bff",
  primaryHover: "#4d84ff",
  primaryActive: "#1f53d6",
  primarySoft: "#eef3ff",
  ink: "#1d2433",
  ink2: "#4b5567",
  muted: "#8a93a6",
  line: "#e8ebf2",
  bgLayout: "#f5f7fb",
};

export const adminTheme: ThemeConfig = {
  token: {
    colorPrimary: BRAND.primary,
    colorInfo: BRAND.primary,
    colorSuccess: "#16a37b",
    colorWarning: "#f59f0a",
    colorError: "#ef4444",
    colorLink: BRAND.primary,
    colorTextBase: BRAND.ink,
    colorTextSecondary: BRAND.ink2,
    colorTextTertiary: BRAND.muted,
    colorBorder: "#dfe3ec",
    colorBorderSecondary: BRAND.line,
    colorBgLayout: BRAND.bgLayout,
    colorBgContainer: "#ffffff",
    colorFillAlter: "#f8f9fc",
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    fontSize: 14,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", "Helvetica Neue", Arial, sans-serif',
    controlHeight: 34,
    boxShadow:
      "0 1px 2px rgba(29, 36, 51, 0.04), 0 4px 16px rgba(29, 36, 51, 0.06)",
    boxShadowSecondary:
      "0 6px 24px rgba(29, 36, 51, 0.10), 0 2px 6px rgba(29, 36, 51, 0.06)",
    motionDurationMid: "0.18s",
  },
  components: {
    Layout: {
      siderBg: "#ffffff",
      headerBg: "rgba(255, 255, 255, 0.86)",
      headerHeight: 56,
      headerPadding: "0 24px",
      bodyBg: BRAND.bgLayout,
      lightSiderBg: "#ffffff",
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
      itemHoverBg: "#f3f5fa",
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
      headerBg: "#f8f9fc",
      headerColor: BRAND.ink2,
      headerSplitColor: "transparent",
      rowHoverBg: "#f7f9ff",
      cellPaddingBlock: 12,
      borderColor: BRAND.line,
    },
    Statistic: {
      titleFontSize: 13,
      contentFontSize: 26,
    },
    Button: {
      fontWeight: 500,
      primaryShadow: "0 2px 6px rgba(47, 107, 255, 0.24)",
    },
    Tag: {
      defaultBg: "#f3f5fa",
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
  "#2f6bff",
  "#7c5cff",
  "#14b8a6",
  "#22c55e",
  "#f59f0a",
  "#ef4444",
  "#ec4899",
  "#0ea5e9",
];
