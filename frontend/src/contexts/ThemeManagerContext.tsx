// Advanced Theme Management Context
// Provides theme switching, persistence, and utilities

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { Theme, ThemeKey, themes, DEFAULT_THEME } from '../styles/themes';
import { applyTheme, getSavedTheme } from '../styles/themeUtils';

interface ThemeContextValue {
  // Current theme state
  currentTheme: Theme;
  currentThemeKey: ThemeKey;
  
  // Theme switching
  setTheme: (themeKey: ThemeKey) => void;
  
  // Available themes
  availableThemes: Record<ThemeKey, Theme>;
  
  // Utility functions
  colors: Theme['colors'];
  isTheme: (themeKey: ThemeKey) => boolean;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

interface ThemeManagerProviderProps {
  children: ReactNode;
  defaultTheme?: ThemeKey;
}

export function ThemeManagerProvider({ 
  children, 
  defaultTheme = DEFAULT_THEME 
}: ThemeManagerProviderProps) {
  // Initialize theme from localStorage or default
  const [currentThemeKey, setCurrentThemeKey] = useState<ThemeKey>(() => {
    const saved = getSavedTheme();
    if (saved && saved in themes) {
      return saved as ThemeKey;
    }
    return defaultTheme;
  });

  const currentTheme = themes[currentThemeKey];

  // Apply theme when it changes
  useEffect(() => {
    applyTheme(currentTheme);
  }, [currentTheme]);

  // Theme switching function
  const setTheme = (themeKey: ThemeKey) => {
    setCurrentThemeKey(themeKey);
  };

  // Utility function to check current theme
  const isTheme = (themeKey: ThemeKey) => currentThemeKey === themeKey;

  const value: ThemeContextValue = {
    currentTheme,
    currentThemeKey,
    setTheme,
    availableThemes: themes,
    colors: currentTheme.colors,
    isTheme,
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
  const { currentTheme, currentThemeKey } = useThemeManager();
  return { theme: currentTheme, key: currentThemeKey };
}

export function useThemeSwitcher() {
  const { setTheme, availableThemes, currentThemeKey } = useThemeManager();
  return { setTheme, availableThemes, currentTheme: currentThemeKey };
}