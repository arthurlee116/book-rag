import type { ThemeConfig } from "antd";

/**
 * ERR Theme - "Secure Data Portal" Aesthetic
 *
 * Design Philosophy: Dark, sophisticated clean-room aesthetic with glowing accents
 * suggesting active monitoring and security. Typography is technical yet refined.
 */
export const darkTheme: ThemeConfig = {
  token: {
    // === Color Architecture ===
    // Primary accent - Electric cyan to blue gradient feel
    colorPrimary: "#00d4ff",
    colorLink: "#3b82f6",
    colorSuccess: "#22c55e",
    colorWarning: "#f59e0b",
    colorError: "#ef4444",
    colorInfo: "#00d4ff",

    // === Background Hierarchy ===
    // Deepest void black - The canvas
    colorBgLayout: "#050507",
    // Elevated surfaces - Panels and cards
    colorBgContainer: "#0d0d12",
    // Hover/interactive states
    colorBgElevated: "#14141a",
    // Spotlight areas
    colorBgSpotlight: "#1a1a24",

    // === Text Colors ===
    // Primary text - Near white for readability
    colorText: "#e5e5e5",
    // Secondary text - Muted but clear
    colorTextSecondary: "#9ca3af",
    // Tertiary text - Subtle labels
    colorTextTertiary: "#6b7280",
    // Quaternary - Borders and dividers
    colorTextQuaternary: "#374151",

    // === Borders ===
    colorBorder: "#1f2937",
    colorBorderSecondary: "#14141a",

    // === Shape ===
    // Slightly more aggressive than Apple style
    borderRadius: 10,
    borderRadiusLG: 14,
    borderRadiusSM: 6,

    // === Typography ===
    // Technical, precise fonts
    fontFamily: 'IBM Plex Mono, -apple-system, BlinkMacSystemFont, "SF Mono", "Monaco", "Menlo", monospace',
    fontSize: 14,
    fontWeightStrong: 600,

    // === Spacing ===
    padding: 16,
    paddingLG: 24,
    paddingSM: 12,
    paddingXS: 8,
    margin: 16,
    marginLG: 24,
    marginSM: 12,

    // === Shadows ===
    // Glowing shadows for accent elements
    boxShadow: "0 0 20px rgba(0, 212, 255, 0.15), 0 4px 12px rgba(0, 0, 0, 0.4)",
    boxShadowSecondary: "0 0 30px rgba(0, 212, 255, 0.1), 0 8px 24px rgba(0, 0, 0, 0.5)",

    // === Motion ===
    motionDurationSlow: "0.4s",
    motionDurationMid: "0.25s",
    motionDurationFast: "0.15s",
  },

  components: {
    Layout: {
      bodyBg: "#050507",
      headerBg: "#0d0d12",
    },

    Card: {
      colorBgContainer: "#0d0d12",
      borderRadiusLG: 14,
      boxShadow: "0 0 20px rgba(0, 212, 255, 0.08), 0 4px 12px rgba(0, 0, 0, 0.3)",
    },

    Button: {
      colorPrimary: "#00d4ff",
      colorPrimaryHover: "#3b82f6",
      colorPrimaryActive: "#0891b2",
      defaultBg: "#14141a",
      defaultBorderColor: "#1f2937",
      defaultColor: "#e5e5e5",
      borderRadius: 8,
      controlHeight: 38,
      fontWeightStrong: 600,
    },

    Input: {
      colorBgContainer: "#0d0d12",
      colorBorder: "#1f2937",
      activeBorderColor: "#00d4ff",
      hoverBorderColor: "#374151",
      borderRadius: 8,
      controlHeight: 42,
      // Subtle glow on focus
      boxShadow: "0 0 0 2px rgba(0, 212, 255, 0.1)",
    },

    Select: {
      colorBgContainer: "#0d0d12",
      colorBgElevated: "#14141a",
      colorBorder: "#1f2937",
      borderRadius: 8,
      controlHeight: 38,
    },

    Tag: {
      borderRadiusSM: 4,
    },

    Alert: {
      borderRadiusLG: 10,
    },

    Typography: {
      colorText: "#e5e5e5",
      colorTextSecondary: "#9ca3af",
      colorTextDescription: "#6b7280",
    },

    Divider: {
      colorSplit: "#1f2937",
    },

    Modal: {
      contentBg: "#0d0d12",
      headerBg: "#0d0d12",
    },

    Tooltip: {
      colorBgSpotlight: "#1a1a24",
    },

    Progress: {
      colorSuccess: "#22c55e",
      colorInfo: "#00d4ff",
    },
  },
};

/**
 * Custom CSS variables for animations and special effects
 */
export const cssVariables = {
  // Gradient definitions
  gradientPrimary: "linear-gradient(135deg, #00d4ff 0%, #3b82f6 100%)",
  gradientSecondary: "linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%)",
  gradientGlow: "linear-gradient(135deg, rgba(0, 212, 255, 0.3) 0%, rgba(59, 130, 246, 0.3) 100%)",

  // Glow intensities
  glowPrimary: "0 0 24px rgba(0, 212, 255, 0.5)",
  glowSecondary: "0 0 20px rgba(139, 92, 246, 0.4)",

  // Animation durations
  animFast: "0.15s",
  animMedium: "0.25s",
  animSlow: "0.4s",
  animSlower: "0.6s",
};
