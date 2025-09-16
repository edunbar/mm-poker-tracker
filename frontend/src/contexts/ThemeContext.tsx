// Backward compatibility wrapper for the new theme system
// This maintains the existing API while using the new centralized theme management

import React from 'react';
import { ThemeManagerProvider, useThemeManager } from './ThemeManagerContext';

// Re-export the new provider as ThemeProvider for backward compatibility
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <ThemeManagerProvider defaultTheme="warm">
      {children}
    </ThemeManagerProvider>
  );
}

// Legacy useTheme hook - maintains backward compatibility
export function useTheme() {
  const { currentThemeKey } = useThemeManager();
  
  return {
    theme: 'light' as const, // For backward compatibility
    // Expose new theme functionality
    currentTheme: currentThemeKey,
    colors: useThemeManager().colors,
    setTheme: useThemeManager().setTheme,
  };
}

// Re-export the new hooks for advanced usage
export { 
  useThemeManager, 
  useThemeColors, 
  useCurrentTheme, 
  useThemeSwitcher 
} from './ThemeManagerContext';