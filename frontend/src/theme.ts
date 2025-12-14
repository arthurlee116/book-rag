import type { ThemeConfig } from "antd";

export const darkTheme: ThemeConfig = {
  token: {
    // 主色 - 柔和的蓝紫色
    colorPrimary: "#6366f1",
    colorLink: "#818cf8",
    colorSuccess: "#22c55e",
    colorWarning: "#f59e0b",
    colorError: "#ef4444",
    colorInfo: "#6366f1",

    // 背景色 - 深色层次
    colorBgContainer: "#1c1c1e",
    colorBgElevated: "#2c2c2e",
    colorBgLayout: "#000000",
    colorBgSpotlight: "#3a3a3c",

    // 文字色
    colorText: "#f5f5f7",
    colorTextSecondary: "#a1a1a6",
    colorTextTertiary: "#6e6e73",
    colorTextQuaternary: "#48484a",

    // 边框
    colorBorder: "#38383a",
    colorBorderSecondary: "#2c2c2e",

    // 圆角 - 苹果风格大圆角
    borderRadius: 12,
    borderRadiusLG: 16,
    borderRadiusSM: 8,

    // 字体
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,

    // 间距
    padding: 16,
    paddingLG: 24,
    paddingSM: 12,
    paddingXS: 8,

    // 阴影 - 柔和
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.32)",
    boxShadowSecondary: "0 4px 16px rgba(0, 0, 0, 0.4)",
  },
  components: {
    Layout: {
      bodyBg: "#000000",
      headerBg: "#1c1c1e",
    },
    Card: {
      colorBgContainer: "#1c1c1e",
      borderRadiusLG: 16,
    },
    Button: {
      colorPrimary: "#6366f1",
      colorPrimaryHover: "#818cf8",
      colorPrimaryActive: "#4f46e5",
      defaultBg: "#2c2c2e",
      defaultBorderColor: "#38383a",
      defaultColor: "#f5f5f7",
      borderRadius: 8,
      controlHeight: 36,
    },
    Input: {
      colorBgContainer: "#1c1c1e",
      colorBorder: "#38383a",
      activeBorderColor: "#6366f1",
      hoverBorderColor: "#48484a",
      borderRadius: 8,
      controlHeight: 40,
    },
    Select: {
      colorBgContainer: "#1c1c1e",
      colorBgElevated: "#2c2c2e",
      colorBorder: "#38383a",
      borderRadius: 8,
      controlHeight: 36,
    },
    Tag: {
      borderRadiusSM: 6,
    },
    Alert: {
      borderRadiusLG: 12,
    },
  },
};
