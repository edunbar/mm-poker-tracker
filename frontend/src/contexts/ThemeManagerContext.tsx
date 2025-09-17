// Simplified Theme Management Context
// Provides the betting site theme and utilities

import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { Theme, themes, DEFAULT_THEME } from '../styles/themes';
import { applyTheme } from '../styles/themeUtils';

interface ThemeContextValue {
  // Current theme state
  currentTheme: Theme;
  currentThemeKey: string;

  // Utility functions
  colors: Theme['colors'];
  setTheme: (themeKey: string) => void;
  availableThemes: string[];
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

interface ThemeManagerProviderProps {
  children: ReactNode;
}

export function ThemeManagerProvider({ children }: ThemeManagerProviderProps) {
  const currentTheme = themes[DEFAULT_THEME];

  // Apply theme on mount
  useEffect(() => {
    applyTheme(currentTheme);
  }, [currentTheme]);

  // Dummy functions for compatibility (since we only have one theme)
  const setTheme = () => {}; // No-op since we only have betting site theme
  const availableThemes = [DEFAULT_THEME];

  const value: ThemeContextValue = {
    currentTheme,
    currentThemeKey: DEFAULT_THEME,
    colors: currentTheme.colors,
    setTheme,
    availableThemes,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

// Hook for consuming theme context
export function useThemeManager(): ThemeContextValue {
  const context = useContext(ThemeContext);

  if (context === undefined) {
    throw new Error('useThemeManager must be used within a ThemeManagerProvider');
  }

  return context;
}

// Convenience hooks for common use cases
export function useThemeColors() {
  const { colors } = useThemeManager();
  return colors;
}

export function useCurrentTheme() {
  const { currentTheme } = useThemeManager();
  return { theme: currentTheme, key: DEFAULT_THEME };
}

export function useThemeSwitcher() {
  const { setTheme, availableThemes, currentThemeKey } = useThemeManager();
  return { setTheme, availableThemes, currentTheme: currentThemeKey };
}