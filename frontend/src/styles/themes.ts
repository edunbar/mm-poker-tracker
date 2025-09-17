// Centralized Theme Management System
// This file defines the betting site theme and its color palette

export interface ThemeColors {
  // Core colors
  background: string;
  foreground: string;

  // Interactive colors
  primary: string;
  primaryForeground: string;
  secondary: string;
  secondaryForeground: string;

  // UI colors
  muted: string;
  mutedForeground: string;
  accent: string;
  accentForeground: string;

  // System colors
  border: string;
  input: string;
  ring: string;

  // Card colors
  card: string;
  cardForeground: string;

  // Status colors
  destructive: string;
  destructiveForeground: string;
  success: string;
  successForeground: string;
  warning: string;
  warningForeground: string;
  info: string;
  infoForeground: string;

  // Navigation colors
  navBackground: string;
  navBorder: string;
  navItemHover: string;
  navItemActive: string;
  navItemActiveBorder: string;
}

export interface Theme {
  name: string;
  description: string;
  colors: ThemeColors;
}

// Betting Site Theme (sports betting inspired)
export const bettingSiteTheme: Theme = {
  name: "Betting Site",
  description: "Dark sports betting theme inspired by FanDuel and DraftKings",
  colors: {
    // Core colors - dark charcoal background like DraftKings
    background: "#1a1a1a", // Dark charcoal background
    foreground: "#FFFFFF", // Pure white text for high contrast

    // Interactive colors - deep purple primary, bright green secondary
    primary: "#8A2BE2", // Deep purple for primary actions
    primaryForeground: "#FFFFFF", // White text on purple
    secondary: "#53d337", // Bright green for secondary actions
    secondaryForeground: "#000000", // Black text on bright green

    // UI colors - dark theme with true gold accents
    muted: "#2a2a2a", // Slightly lighter gray for muted areas
    mutedForeground: "#B0B0B0", // Light gray for muted text
    accent: "#D4B574", // Sophisticated gold for accents
    accentForeground: "#000000", // Black text on gold

    // System colors
    border: "#404040", // Medium gray for borders
    input: "#2a2a2a", // Dark gray for inputs
    ring: "#8A2BE2", // Purple for focus rings

    // Card colors - slightly lighter than background for depth
    card: "#242424", // DraftKings card background
    cardForeground: "#FFFFFF", // White text on cards

    // Status colors - vibrant for betting interface
    destructive: "#DC2626",
    destructiveForeground: "#FFFFFF",
    success: "#53d337", // Bright green for success
    successForeground: "#000000",
    warning: "#D4B574", // Sophisticated gold for warnings
    warningForeground: "#000000",
    info: "#1E90FF", // Bright blue for info
    infoForeground: "#FFFFFF",

    // Navigation colors - dark with purple accents
    navBackground: "#242424", // Slightly lighter than main background
    navBorder: "#404040",
    navItemHover: "#2a2a2a", // Subtle hover state
    navItemActive: "#8A2BE2", // Purple for active items
    navItemActiveBorder: "#D4B574", // Sophisticated gold border for active
  }
};

// Available themes registry - only betting site theme
export const themes = {
  bettingSite: bettingSiteTheme,
} as const;

export type ThemeKey = keyof typeof themes;

// Default theme
export const DEFAULT_THEME: ThemeKey = 'bettingSite';