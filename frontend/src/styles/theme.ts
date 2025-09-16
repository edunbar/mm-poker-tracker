// Global theme system inspired by Airtable, Stripe, Linear, and GitHub
// Light mode only for clean, professional appearance

export const theme = {
  // Color system inspired by Linear + GitHub
  colors: {
    // Neutral grays (Linear inspired)
    neutral: {
      50: '#fafafa',
      100: '#f5f5f5',
      200: '#e5e5e5',
      300: '#d4d4d4',
      400: '#a3a3a3',
      500: '#737373',
      600: '#525252',
      700: '#404040',
      800: '#262626',
      900: '#171717',
    },
    
    // Primary blue (Linear + GitHub inspired)
    primary: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
    },
    
    // Success green (GitHub inspired)
    success: {
      50: '#f0fdf4',
      100: '#dcfce7',
      200: '#bbf7d0',
      300: '#86efac',
      400: '#4ade80',
      500: '#22c55e',
      600: '#16a34a',
      700: '#15803d',
      800: '#166534',
      900: '#14532d',
    },
    
    // Warning amber
    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      200: '#fde68a',
      300: '#fcd34d',
      400: '#fbbf24',
      500: '#f59e0b',
      600: '#d97706',
      700: '#b45309',
      800: '#92400e',
      900: '#78350f',
    },
    
    // Error red (GitHub inspired)
    error: {
      50: '#fef2f2',
      100: '#fee2e2',
      200: '#fecaca',
      300: '#fca5a5',
      400: '#f87171',
      500: '#ef4444',
      600: '#dc2626',
      700: '#b91c1c',
      800: '#991b1b',
      900: '#7f1d1d',
    },
    
    // Special colors for GitHub-style labels
    labels: {
      bug: '#d73a49',
      feature: '#0366d6',
      enhancement: '#a2eeef',
      documentation: '#0075ca',
      help: '#008672',
      invalid: '#e4e669',
      question: '#d876e3',
      wontfix: '#ffffff',
    }
  },
  
  // Typography system (Linear inspired)
  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Menlo', 'monospace'],
    },
    fontSize: {
      xs: ['11px', '16px'],
      sm: ['13px', '18px'],
      base: ['14px', '20px'],
      lg: ['16px', '24px'],
      xl: ['18px', '28px'],
      '2xl': ['20px', '28px'],
      '3xl': ['24px', '32px'],
      '4xl': ['28px', '36px'],
    },
    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
  },
  
  // Spacing system (Linear + Airtable inspired)
  spacing: {
    px: '1px',
    0: '0',
    0.5: '2px',
    1: '4px',
    1.5: '6px',
    2: '8px',
    2.5: '10px',
    3: '12px',
    3.5: '14px',
    4: '16px',
    5: '20px',
    6: '24px',
    7: '28px',
    8: '32px',
    9: '36px',
    10: '40px',
    11: '44px',
    12: '48px',
    14: '56px',
    16: '64px',
    20: '80px',
    24: '96px',
    28: '112px',
    32: '128px',
  },
  
  // Border radius (Linear inspired)
  borderRadius: {
    none: '0',
    sm: '2px',
    base: '4px',
    md: '6px',
    lg: '8px',
    xl: '12px',
    '2xl': '16px',
    full: '9999px',
  },
  
  // Shadows (Stripe inspired)
  boxShadow: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    base: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
    none: 'none',
  },
  
  // Component-specific tokens
  components: {
    // Airtable-inspired table styles
    table: {
      headerHeight: '40px',
      rowHeight: '44px',
      borderColor: '#e5e5e5',
      hoverColor: '#f9f9f9',
      selectedColor: '#f0f9ff',
      sortableHover: '#f5f5f5',
    },
    
    // Stripe-inspired card styles
    card: {
      borderRadius: '8px',
      borderColor: '#e5e5e5',
      backgroundColor: '#ffffff',
      shadowHover: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    },
    
    // Linear-inspired button styles
    button: {
      primary: {
        backgroundColor: '#171717',
        hoverBackgroundColor: '#262626',
        textColor: '#ffffff',
        borderRadius: '6px',
        height: '36px',
        fontSize: '14px',
        fontWeight: '500',
      },
      secondary: {
        backgroundColor: '#ffffff',
        hoverBackgroundColor: '#f5f5f5',
        textColor: '#171717',
        borderColor: '#e5e5e5',
        borderRadius: '6px',
        height: '36px',
        fontSize: '14px',
        fontWeight: '500',
      },
    },
    
    // GitHub-inspired badge/label styles
    badge: {
      borderRadius: '12px',
      fontSize: '12px',
      fontWeight: '500',
      padding: '2px 8px',
      colors: {
        default: {
          backgroundColor: '#f1f3f4',
          textColor: '#5f6368',
        },
        primary: {
          backgroundColor: '#e8f0fe',
          textColor: '#1a73e8',
        },
        success: {
          backgroundColor: '#e6f4ea',
          textColor: '#137333',
        },
        warning: {
          backgroundColor: '#fef7e0',
          textColor: '#ea8600',
        },
        error: {
          backgroundColor: '#fce8e6',
          textColor: '#d93025',
        },
      },
    },
    
    // Linear-inspired input styles
    input: {
      height: '36px',
      borderRadius: '6px',
      borderColor: '#e5e5e5',
      focusBorderColor: '#2563eb',
      backgroundColor: '#ffffff',
      fontSize: '14px',
      paddingX: '12px',
    },
    
    // Navigation styles (inspired by all platforms)
    navigation: {
      height: '60px',
      backgroundColor: '#ffffff',
      borderColor: '#e5e5e5',
      itemHeight: '36px',
      itemBorderRadius: '6px',
      itemHoverColor: '#f5f5f5',
      itemActiveColor: '#f0f9ff',
      itemActiveBorderColor: '#2563eb',
    },
  },
  
  // Animation and transitions
  animation: {
    transition: {
      fast: '150ms ease',
      normal: '200ms ease',
      slow: '300ms ease',
    },
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    },
  },
} as const;

export type Theme = typeof theme;

// Helper functions for consistent styling
export const createComponentStyles = {
  // Airtable-inspired table cell
  tableCell: (options?: { isHeader?: boolean; isSelected?: boolean; isSortable?: boolean }) => ({
    height: options?.isHeader ? theme.components.table.headerHeight : theme.components.table.rowHeight,
    borderColor: theme.components.table.borderColor,
    backgroundColor: options?.isSelected ? theme.components.table.selectedColor : 'transparent',
    '&:hover': options?.isSortable ? {
      backgroundColor: theme.components.table.sortableHover,
    } : undefined,
  }),
  
  // Stripe-inspired card
  card: (elevated = false) => ({
    backgroundColor: theme.components.card.backgroundColor,
    borderRadius: theme.components.card.borderRadius,
    borderColor: theme.components.card.borderColor,
    borderWidth: '1px',
    boxShadow: elevated ? theme.components.card.shadowHover : theme.boxShadow.sm,
  }),
  
  // Linear-inspired button
  button: (variant: 'primary' | 'secondary' = 'primary') => {
    const config = theme.components.button[variant];
    return {
      backgroundColor: config.backgroundColor,
      color: config.textColor,
      borderRadius: config.borderRadius,
      height: config.height,
      fontSize: config.fontSize,
      fontWeight: config.fontWeight,
      borderColor: 'borderColor' in config ? config.borderColor : 'transparent',
      borderWidth: 'borderColor' in config ? '1px' : '0',
      '&:hover': {
        backgroundColor: config.hoverBackgroundColor,
      },
    };
  },
  
  // GitHub-inspired badge
  badge: (variant: keyof typeof theme.components.badge.colors = 'default') => {
    const config = theme.components.badge.colors[variant];
    return {
      backgroundColor: config.backgroundColor,
      color: config.textColor,
      borderRadius: theme.components.badge.borderRadius,
      fontSize: theme.components.badge.fontSize,
      fontWeight: theme.components.badge.fontWeight,
      padding: theme.components.badge.padding,
    };
  },
};