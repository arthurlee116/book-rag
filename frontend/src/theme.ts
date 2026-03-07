import type { ThemeConfig } from "antd";

/**
 * ERR Theme - "Warm Vault" Aesthetic
 *
 * Design Philosophy: Deep, warm dark surfaces with amber/gold accents
 * suggesting trust, warmth, and privacy. Typography is elegant yet readable.
 * Replaces the cold cyan/purple "AI wrapper" look with an organic, premium feel.
 */
export const darkTheme: ThemeConfig = {
  token: {
    // === Color Architecture ===
    // Primary accent - Warm amber/gold
    colorPrimary: "#D4915C",
    colorLink: "#E8A96B",
    colorSuccess: "#6BBF7A",
    colorWarning: "#E8B84B",
    colorError: "#D96B6B",
    colorInfo: "#D4915C",

    // === Background Hierarchy ===
    // Deep warm charcoal - The canvas
    colorBgLayout: "#111110",
    // Elevated surfaces - Panels and cards
    colorBgContainer: "#1A1918",
    // Hover/interactive states
    colorBgElevated: "#222120",
    // Spotlight areas
    colorBgSpotlight: "#2A2827",

    // === Text Colors ===
    // Primary text - Warm white for readability
    colorText: "#ECE8E1",
    // Secondary text - Muted warm gray
    colorTextSecondary: "#A8A29E",
    // Tertiary text - Subtle labels
    colorTextTertiary: "#8C8580",  // Raised from #78716C → WCAG AA ≈5.1:1 on #111110
    // Quaternary - Borders and dividers
    colorTextQuaternary: "#44403C",

    // === Borders ===
    colorBorder: "#2E2B28",
    colorBorderSecondary: "#1A1918",

    // === Shape ===
    borderRadius: 12,
    borderRadiusLG: 16,
    borderRadiusSM: 8,

    // === Typography ===
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
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
    // Warm ambient shadows
    boxShadow: "0 4px 24px rgba(0, 0, 0, 0.25), 0 0 12px rgba(212, 145, 92, 0.06)",
    boxShadowSecondary: "0 8px 32px rgba(0, 0, 0, 0.35), 0 0 20px rgba(212, 145, 92, 0.04)",

    // === Motion ===
    motionDurationSlow: "0.4s",
    motionDurationMid: "0.25s",
    motionDurationFast: "0.15s",
  },

  components: {
    Layout: {
      bodyBg: "#111110",
      headerBg: "#1A1918",
    },

    Card: {
      colorBgContainer: "#1A1918",
      borderRadiusLG: 16,
      boxShadow: "0 4px 20px rgba(0, 0, 0, 0.2), 0 0 8px rgba(212, 145, 92, 0.04)",
    },

    Button: {
      colorPrimary: "#D4915C",
      colorPrimaryHover: "#E8A96B",
      colorPrimaryActive: "#B87A4A",
      defaultBg: "#222120",
      defaultBorderColor: "#2E2B28",
      defaultColor: "#ECE8E1",
      borderRadius: 10,
      controlHeight: 40,
      fontWeightStrong: 600,
    },

    Input: {
      colorBgContainer: "#1A1918",
      colorBorder: "#2E2B28",
      activeBorderColor: "#D4915C",
      hoverBorderColor: "#44403C",
      borderRadius: 10,
      controlHeight: 44,
      boxShadow: "0 0 0 2px rgba(212, 145, 92, 0.08)",
    },

    Select: {
      colorBgContainer: "#1A1918",
      colorBgElevated: "#222120",
      colorBorder: "#2E2B28",
      borderRadius: 10,
      controlHeight: 40,
    },

    Tag: {
      borderRadiusSM: 6,
    },

    Alert: {
      borderRadiusLG: 12,
    },

    Typography: {
      colorText: "#ECE8E1",
      colorTextSecondary: "#A8A29E",
      colorTextDescription: "#8C8580",
    },

    Divider: {
      colorSplit: "#2E2B28",
    },

    Modal: {
      contentBg: "#1A1918",
      headerBg: "#1A1918",
    },

    Tooltip: {
      colorBgSpotlight: "#2A2827",
    },

    Progress: {
      colorSuccess: "#6BBF7A",
      colorInfo: "#D4915C",
    },
  },
};

/**
 * Custom CSS variables for animations and special effects
 */
export const cssVariables = {
  // Gradient definitions
  gradientPrimary: "linear-gradient(135deg, #D4915C 0%, #E8A96B 100%)",
  gradientSecondary: "linear-gradient(135deg, #B87A4A 0%, #D4915C 100%)",
  gradientGlow: "linear-gradient(135deg, rgba(212, 145, 92, 0.2) 0%, rgba(232, 169, 107, 0.2) 100%)",

  // Glow intensities
  glowPrimary: "0 0 20px rgba(212, 145, 92, 0.35)",
  glowSecondary: "0 0 16px rgba(184, 122, 74, 0.25)",

  // Animation durations
  animFast: "0.15s",
  animMedium: "0.25s",
  animSlow: "0.4s",
  animSlower: "0.6s",
};

/**
 * Central token reference for components.
 * Importing from here instead of hard-coding hex strings ensures a single
 * source of truth — changing a value here propagates everywhere.
 */
export const themeTokens = {
  // === Backgrounds ===
  bgLayout: "#111110",
  bgContainer: "#1A1918",
  bgElevated: "#222120",
  bgSpotlight: "#2A2827",

  // === Text ===
  textPrimary: "#ECE8E1",
  textSecondary: "#A8A29E",
  textTertiary: "#8C8580",   // WCAG AA compliant on bgLayout
  textOnAccent: "#111110",   // Text placed on amber accent backgrounds

  // === Accent / Brand ===
  accentPrimary: "#D4915C",
  accentHover: "#E8A96B",
  accentActive: "#B87A4A",

  // === Borders ===
  border: "#2E2B28",
  borderSecondary: "#1A1918",
  borderQuaternary: "#44403C",

  // === Semantic ===
  colorSuccess: "#6BBF7A",
  colorWarning: "#E8B84B",
  colorError: "#D96B6B",

  // === Surfaces (rgba helpers) ===
  surfaceContainer: "rgba(26, 25, 24, 0.5)",
  surfaceContainerSolid: "rgba(26, 25, 24, 0.7)",
  surfaceAccentSubtle: "rgba(212, 145, 92, 0.06)",
  surfaceErrorSubtle: "rgba(217, 107, 107, 0.08)",
  borderErrorSubtle: "rgba(217, 107, 107, 0.2)",

  // === Gradients ===
  gradientAccent: "linear-gradient(135deg, #D4915C 0%, #E8A96B 100%)",
} as const;
