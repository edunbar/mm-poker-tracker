// Centralized Theme Management System
// This file defines all available themes and their color palettes

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

// Warm Professional Theme (current)
export const warmTheme: Theme = {
  name: "Warm Professional",
  description: "Warm, inviting palette with slate blue accents",
  colors: {
    // Core colors - warm off-white background with dark navy text
    background: "#F9F3EF",
    foreground: "#1B3C53",
    
    // Interactive colors - slate blue as primary
    primary: "#456882",
    primaryForeground: "#FFFFFF", 
    secondary: "#D2C1B6",
    secondaryForeground: "#1B3C53",
    
    // UI colors - warm beige tones
    muted: "#D2C1B6",
    mutedForeground: "#6B7C93", // Muted version of dark navy
    accent: "#E8DDD6", // Lighter warm beige
    accentForeground: "#1B3C53",
    
    // System colors
    border: "#E0D2C7", // Lighter version of warm beige
    input: "#E0D2C7",
    ring: "#456882", // Slate blue for focus
    
    // Card colors - clean white on warm background
    card: "#FFFFFF",
    cardForeground: "#1B3C53",
    
    // Status colors - adapted to warm palette
    destructive: "#DC2626",
    destructiveForeground: "#FFFFFF",
    success: "#059669", 
    successForeground: "#FFFFFF",
    warning: "#D97706",
    warningForeground: "#FFFFFF", 
    info: "#456882", // Use our slate blue
    infoForeground: "#FFFFFF",
    
    // Navigation colors
    navBackground: "#FFFFFF",
    navBorder: "#E0D2C7",
    navItemHover: "#D2C1B6",
    navItemActive: "#D2C1B6",
    navItemActiveBorder: "#456882",
  }
};

// Cool Modern Theme (alternative)
export const coolTheme: Theme = {
  name: "Cool Modern", 
  description: "Clean, modern palette with blue-gray tones",
  colors: {
    background: "#F8FAFC",
    foreground: "#1E293B",
    
    primary: "#3B82F6",
    primaryForeground: "#FFFFFF",
    secondary: "#E2E8F0", 
    secondaryForeground: "#1E293B",
    
    muted: "#E2E8F0",
    mutedForeground: "#64748B",
    accent: "#F1F5F9",
    accentForeground: "#1E293B",
    
    border: "#E2E8F0",
    input: "#E2E8F0", 
    ring: "#3B82F6",
    
    card: "#FFFFFF",
    cardForeground: "#1E293B",
    
    destructive: "#EF4444",
    destructiveForeground: "#FFFFFF",
    success: "#10B981",
    successForeground: "#FFFFFF", 
    warning: "#F59E0B",
    warningForeground: "#FFFFFF",
    info: "#3B82F6",
    infoForeground: "#FFFFFF",
    
    navBackground: "#FFFFFF", 
    navBorder: "#E2E8F0",
    navItemHover: "#F1F5F9",
    navItemActive: "#DBEAFE",
    navItemActiveBorder: "#3B82F6",
  }
};

// Classic Theme (GitHub-inspired)
export const classicTheme: Theme = {
  name: "Classic",
  description: "Clean, high-contrast palette inspired by GitHub",
  colors: {
    background: "#FFFFFF",
    foreground: "#24292F",
    
    primary: "#0969DA",
    primaryForeground: "#FFFFFF",
    secondary: "#F6F8FA",
    secondaryForeground: "#24292F",
    
    muted: "#F6F8FA", 
    mutedForeground: "#656D76",
    accent: "#F3F4F6",
    accentForeground: "#24292F",
    
    border: "#D0D7DE",
    input: "#D0D7DE",
    ring: "#0969DA",
    
    card: "#FFFFFF",
    cardForeground: "#24292F",
    
    destructive: "#DA3633",
    destructiveForeground: "#FFFFFF",
    success: "#1A7F37", 
    successForeground: "#FFFFFF",
    warning: "#D1242F",
    warningForeground: "#FFFFFF",
    info: "#0969DA",
    infoForeground: "#FFFFFF",
    
    navBackground: "#FFFFFF",
    navBorder: "#D0D7DE", 
    navItemHover: "#F3F4F6",
    navItemActive: "#DBEAFE",
    navItemActiveBorder: "#0969DA",
  }
};

// Neutral Gold Theme (new)
export const neutralGoldTheme: Theme = {
  name: "Dark Gold",
  description: "Sophisticated dark theme with gold accents",
  colors: {
    // Core colors - dark background with light text
    background: "#434343", // Dark gray background
    foreground: "#F8F8F8", // Light gray for text
    
    // Interactive colors - true gold as primary
    primary: "#D4B574", // True gold tone
    primaryForeground: "#434343", // Dark gray text on gold
    secondary: "#5A5A5A", // Slightly lighter gray
    secondaryForeground: "#F8F8F8", // Light text
    
    // UI colors - darker tones for dark theme
    muted: "#5A5A5A", // Slightly lighter gray for muted backgrounds
    mutedForeground: "#C0C0C0", // Light gray for muted text
    accent: "#6B6B6B", // Medium gray for accents
    accentForeground: "#F8F8F8",
    
    // System colors
    border: "#6B6B6B", // Medium gray borders
    input: "#5A5A5A", // Slightly lighter input backgrounds
    ring: "#D4B574", // Sophisticated gold for focus rings
    
    // Card colors - slightly lighter than background
    card: "#5A5A5A", // Slightly lighter gray for cards
    cardForeground: "#F8F8F8", // Light text on cards
    
    // Status colors - adapted to neutral palette
    destructive: "#DC2626",
    destructiveForeground: "#FFFFFF",
    success: "#059669", 
    successForeground: "#FFFFFF",
    warning: "#D4B574", // Use our true gold for warnings
    warningForeground: "#434343",
    info: "#6B6B6B", // Medium gray for info
    infoForeground: "#FFFFFF",
    
    // Navigation colors
    navBackground: "#5A5A5A", // Slightly lighter than main background
    navBorder: "#6B6B6B",
    navItemHover: "#6B6B6B", // Medium gray hover
    navItemActive: "#D4B574", // Sophisticated gold for active items
    navItemActiveBorder: "#B89C5A", // Deeper gold border
  }
};

// Muted Earth Theme (new custom palette)
export const mutedEarthTheme: Theme = {
  name: "Muted Earth",
  description: "Earthy, muted tones with warm gold accents",
  colors: {
    // Core colors - using the muted grays as base
    background: "#797c7f", // Medium gray from palette
    foreground: "#D4B574", // Sophisticated gold for primary text
    
    // Interactive colors - true gold as primary
    primary: "#D4B574", // Sophisticated gold for primary actions
    primaryForeground: "#8c8e91", // Dark gray text on gold
    secondary: "#889294", // Blue-gray secondary
    secondaryForeground: "#D4B574", // Sophisticated gold text on secondary
    
    // UI colors - using the earth tones
    muted: "#95888b", // Muted brown-gray
    mutedForeground: "#D4B574", // Sophisticated gold text on muted
    accent: "#849884", // Sage green for accents
    accentForeground: "#D4B574", // Sophisticated gold text on green
    
    // System colors
    border: "#768083", // Darker gray for borders
    input: "#847579", // Brown-gray for inputs
    ring: "#D4B574", // Sophisticated gold for focus rings
    
    // Card colors - slightly lighter than background
    card: "#8c8e91", // Light gray for cards
    cardForeground: "#D4B574", // Sophisticated gold text on cards
    
    // Status colors - adapted to earthy palette
    destructive: "#DC2626",
    destructiveForeground: "#FFFFFF",
    success: "#718871", // Green from palette
    successForeground: "#FFFFFF",
    warning: "#D4B574", // Sophisticated gold for warnings
    warningForeground: "#8c8e91",
    info: "#849884", // Sage green for info
    infoForeground: "#FFFFFF",
    
    // Navigation colors
    navBackground: "#8c8e91", // Light gray nav
    navBorder: "#768083",
    navItemHover: "#95888b", // Brown-gray hover
    navItemActive: "#D4B574", // Sophisticated gold for active items
    navItemActiveBorder: "#B89C5A", // Deeper gold border
  }
};

// Professional Dark Theme (updated custom palette)
export const professionalDarkTheme: Theme = {
  name: "Professional Dark",
  description: "Sophisticated theme with blue, gold, and balanced grays",
  colors: {
    // Core colors - using the new palette
    background: "#cccccc", // Light gray background
    foreground: "#333333", // Dark gray text for contrast
    
    // Interactive colors - blue and true gold
    primary: "#D4B574", // Sophisticated gold for primary actions
    primaryForeground: "#333333", // Dark text on gold
    secondary: "#336699", // Blue secondary
    secondaryForeground: "#FFFFFF", // White text on blue
    
    // UI colors - variations using the palette
    muted: "#bbbbbb", // Slightly darker light gray for muted areas
    mutedForeground: "#333333", // Dark gray for muted text
    accent: "#4a7db8", // Lighter blue for accents
    accentForeground: "#FFFFFF", // White text on accent
    
    // System colors
    border: "#aaaaaa", // Medium gray for borders
    input: "#bbbbbb", // Light gray for inputs
    ring: "#D4B574", // Sophisticated gold for focus rings
    
    // Card colors - clean white on light background
    card: "#FFFFFF", // White cards
    cardForeground: "#333333", // Dark text on cards
    
    // Status colors - adapted to new palette
    destructive: "#DC2626",
    destructiveForeground: "#FFFFFF",
    success: "#059669", 
    successForeground: "#FFFFFF",
    warning: "#D4B574", // Use true gold for warnings
    warningForeground: "#333333",
    info: "#336699", // Blue for info
    infoForeground: "#FFFFFF",
    
    // Navigation colors
    navBackground: "#FFFFFF", // White nav background
    navBorder: "#aaaaaa",
    navItemHover: "#bbbbbb", // Light gray hover
    navItemActive: "#D4B574", // Sophisticated gold for active items
    navItemActiveBorder: "#B89C5A", // Deeper gold border for active
  }
};

// Professional Office Theme (new custom palette)
export const professionalOfficeTheme: Theme = {
  name: "Professional Office",
  description: "Dark professional theme with green primary and gold accents",
  colors: {
    // Core colors - black base with light text
    background: "#07020D", // Black background
    foreground: "#CDD1C4", // Light ash gray text for contrast
    
    // Interactive colors - green primary, blue secondary
    primary: "#157F1F", // Office green for primary actions
    primaryForeground: "#FFFFFF", // White text on green
    secondary: "#5C80BC", // Glaucous blue for secondary actions
    secondaryForeground: "#FFFFFF", // White text on blue
    
    // UI colors - using true gold as main accent
    muted: "#1a1a1a", // Dark gray for muted areas (slightly lighter than background)
    mutedForeground: "#CDD1C4", // Light gray for muted text
    accent: "#D4B574", // Sophisticated gold for accents
    accentForeground: "#000000", // Pure black text on gold for maximum contrast
    
    // System colors
    border: "#333333", // Dark gray for borders
    input: "#1a1a1a", // Dark gray for inputs
    ring: "#157F1F", // Green for focus rings
    
    // Card colors - slightly lighter than background
    card: "#1a1a1a", // Dark gray cards
    cardForeground: "#CDD1C4", // Light text on cards
    
    // Status colors - adapted to dark theme
    destructive: "#DC2626",
    destructiveForeground: "#FFFFFF",
    success: "#157F1F", // Office green for success
    successForeground: "#FFFFFF",
    warning: "#D4B574", // Sophisticated gold for warnings
    warningForeground: "#000000", // Pure black text on gold
    info: "#5C80BC", // Glaucous blue for info
    infoForeground: "#FFFFFF",
    
    // Navigation colors
    navBackground: "#1a1a1a", // Dark gray nav background
    navBorder: "#333333",
    navItemHover: "#2a2a2a", // Lighter dark gray hover
    navItemActive: "#157F1F", // Green for active items  
    navItemActiveBorder: "#D4B574", // Sophisticated gold border for active
  }
};

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

// Available themes registry
export const themes = {
  warm: warmTheme,
  cool: coolTheme, 
  classic: classicTheme,
  neutralGold: neutralGoldTheme,
  mutedEarth: mutedEarthTheme,
  professionalDark: professionalDarkTheme,
  professionalOffice: professionalOfficeTheme,
  bettingSite: bettingSiteTheme,
} as const;

export type ThemeKey = keyof typeof themes;

// Default theme
export const DEFAULT_THEME: ThemeKey = 'warm';