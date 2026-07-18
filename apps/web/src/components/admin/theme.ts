import type { ThemeConfig } from "antd";

/** Ant Design Pro–inspired enterprise admin theme (zh-CN). */
export const adminTheme: ThemeConfig = {
  token: {
    colorPrimary: "#1677ff",
    colorSuccess: "#52c41a",
    colorWarning: "#faad14",
    colorError: "#ff4d4f",
    colorInfo: "#1677ff",
    borderRadius: 8,
    fontFamily:
      '"Segoe UI", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif',
    colorBgLayout: "#f0f2f5",
    colorBgContainer: "#ffffff",
  },
  components: {
    Layout: {
      siderBg: "#001529",
      triggerBg: "#002140",
      headerBg: "#ffffff",
      bodyBg: "#f0f2f5",
    },
    Menu: {
      darkItemBg: "#001529",
      darkSubMenuItemBg: "#000c17",
      darkItemSelectedBg: "#1677ff",
      itemBorderRadius: 6,
    },
    Card: {
      borderRadiusLG: 10,
    },
    Statistic: {
      titleFontSize: 13,
    },
  },
};

export const CHART_COLORS = [
  "#1677ff",
  "#722ed1",
  "#13c2c2",
  "#52c41a",
  "#faad14",
  "#ff4d4f",
  "#eb2f96",
  "#2f54eb",
];
