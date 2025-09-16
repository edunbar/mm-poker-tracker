// Theme Utilities
// Helper functions for theme management and CSS generation

import { Theme, ThemeColors } from './themes';

/**
 * Converts hex color to HSL format for CSS custom properties
 * Example: "#F9F3EF" -> "28 25% 96%"
 */
export function hexToHsl(hex: string): string {
  // Remove # if present
  hex = hex.replace('#', '');
  
  // Parse RGB values
  const r = parseInt(hex.substr(0, 2), 16) / 255;
  const g = parseInt(hex.substr(2, 2), 16) / 255;
  const b = parseInt(hex.substr(4, 2), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h: number, s: number, l: number;

  l = (max + min) / 2;

  if (max === min) {
    h = s = 0; // achromatic
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
      default: h = 0;
    }
    h /= 6;
  }

  // Convert to degrees and percentages
  h = Math.round(h * 360);
  s = Math.round(s * 100);
  l = Math.round(l * 100);

  return `${h} ${s}% ${l}%`;
}

/**
 * Converts theme colors to CSS custom properties
 */
export function themeToCSS(theme: Theme): Record<string, string> {
  const { colors } = theme;
  
  return {
    // Core colors
    '--background': hexToHsl(colors.background),
    '--foreground': hexToHsl(colors.foreground),
    
    // Interactive colors
    '--primary': hexToHsl(colors.primary),
    '--primary-foreground': hexToHsl(colors.primaryForeground),
    '--secondary': hexToHsl(colors.secondary), 
    '--secondary-foreground': hexToHsl(colors.secondaryForeground),
    
    // UI colors
    '--muted': hexToHsl(colors.muted),
    '--muted-foreground': hexToHsl(colors.mutedForeground),
    '--accent': hexToHsl(colors.accent),
    '--accent-foreground': hexToHsl(colors.accentForeground),
    
    // System colors
    '--border': hexToHsl(colors.border),
    '--input': hexToHsl(colors.input),
    '--ring': hexToHsl(colors.ring),
    
    // Card colors
    '--card': hexToHsl(colors.card),
    '--card-foreground': hexToHsl(colors.cardForeground),
    
    // Status colors
    '--destructive': hexToHsl(colors.destructive),
    '--destructive-foreground': hexToHsl(colors.destructiveForeground),
    '--success': hexToHsl(colors.success),
    '--success-foreground': hexToHsl(colors.successForeground),
    '--warning': hexToHsl(colors.warning),
    '--warning-foreground': hexToHsl(colors.warningForeground),
    '--info': hexToHsl(colors.info),
    '--info-foreground': hexToHsl(colors.infoForeground),
    
    // Navigation colors
    '--nav-background': hexToHsl(colors.navBackground),
    '--nav-border': hexToHsl(colors.navBorder),
    '--nav-item-hover': hexToHsl(colors.navItemHover),
    '--nav-item-active': hexToHsl(colors.navItemActive),
    '--nav-item-active-border': hexToHsl(colors.navItemActiveBorder),
    
    // Legacy support - keep some old variables for compatibility
    '--popover': hexToHsl(colors.card),
    '--popover-foreground': hexToHsl(colors.cardForeground),
    '--radius': '0.5rem',
  };
}

/**
 * Applies theme to the document root
 */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  const cssVars = themeToCSS(theme);
  
  Object.entries(cssVars).forEach(([property, value]) => {
    root.style.setProperty(property, value);
  });
  
  // Store theme preference
  localStorage.setItem('theme', theme.name);
}

/**
 * Gets the saved theme preference from localStorage
 */
export function getSavedTheme(): string | null {
  return localStorage.getItem('theme');
}

/**
 * Generates utility classes for theme colors
 */
export function generateColorUtilities(colors: ThemeColors): string {
  return `
  /* Theme-aware utility classes */
  .bg-theme-primary { background-color: ${colors.primary}; }
  .bg-theme-secondary { background-color: ${colors.secondary}; }
  .bg-theme-accent { background-color: ${colors.accent}; }
  .bg-theme-muted { background-color: ${colors.muted}; }
  
  .text-theme-primary { color: ${colors.primary}; }
  .text-theme-secondary { color: ${colors.secondary}; }  
  .text-theme-accent { color: ${colors.accent}; }
  .text-theme-muted { color: ${colors.mutedForeground}; }
  
  .border-theme-primary { border-color: ${colors.primary}; }
  .border-theme-secondary { border-color: ${colors.secondary}; }
  .border-theme-accent { border-color: ${colors.accent}; }
  `;
}

/**
 * Theme-aware component class generators
 */
export const themeClasses = {
  button: {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80', 
    outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
    ghost: 'hover:bg-accent hover:text-accent-foreground',
  },
  
  card: 'bg-card text-card-foreground border border-border',
  
  input: 'border-input bg-background focus:ring-ring',
  
  nav: {
    item: 'hover:bg-nav-item-hover',
    active: 'bg-nav-item-active border-l-2 border-nav-item-active-border',
  }
} as const;