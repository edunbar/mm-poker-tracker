// Simplified theme context for the betting site theme

import React from 'react';
import { ThemeManagerProvider, useThemeManager } from './ThemeManagerContext';

// Re-export the new provider as ThemeProvider for backward compatibility
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <ThemeManagerProvider>
      {children}
    </ThemeManagerProvider>
  );
}

// Legacy useTheme hook - maintains backward compatibility
export function useTheme() {
  const { currentThemeKey, colors, setTheme } = useThemeManager();

  return {
    theme: 'light' as const, // For backward compatibility
    currentTheme: currentThemeKey,
    colors,
    setTheme,
  };
}

// Re-export the new hooks for advanced usage
export {
  useThemeManager,
  useThemeColors,
  useCurrentTheme,
  useThemeSwitcher
} from './ThemeManagerContext';