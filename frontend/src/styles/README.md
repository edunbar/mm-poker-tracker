# Centralized Theme Management System

This advanced theme system makes it incredibly easy to change colors, add new themes, and maintain design consistency across your poker analytics application.

## 🎨 Quick Theme Changes

### Adding a New Theme

1. **Define your theme** in `src/styles/themes.ts`:

```typescript
export const myCustomTheme: Theme = {
  name: "My Custom Theme",
  description: "A beautiful custom palette",
  colors: {
    background: "#F5F5F5",
    foreground: "#2D2D2D", 
    primary: "#FF6B6B",
    // ... other colors
  }
};

// Add to themes registry
export const themes = {
  warm: warmTheme,
  cool: coolTheme,
  classic: classicTheme,
  custom: myCustomTheme, // ← Add your theme here
} as const;
```

2. **That's it!** Your theme is now available throughout the app.

### Using Themes in Components

#### Option 1: Theme-aware components (Recommended)
```tsx
import { ThemeButton } from '../components/ui/ThemeButton';

// Automatically uses current theme colors
<ThemeButton variant="primary">Save</ThemeButton>
```

#### Option 2: Theme hooks
```tsx
import { useThemeColors } from '../contexts/ThemeContext';

function MyComponent() {
  const colors = useThemeColors();
  
  return (
    <div style={{ backgroundColor: colors.background, color: colors.foreground }}>
      Content
    </div>
  );
}
```

#### Option 3: CSS custom properties (Most flexible)
```tsx
// These automatically update when theme changes
<div className="bg-background text-foreground border-border">
  <button className="bg-primary text-primary-foreground">
    Click me
  </button>
</div>
```

## 🛠 Available Hooks

### `useThemeColors()`
Get all colors from the current theme:
```tsx
const colors = useThemeColors();
console.log(colors.primary); // "#456882"
```

### `useThemeSwitcher()`
Control theme switching:
```tsx
const { setTheme, availableThemes, currentTheme } = useThemeSwitcher();

// Switch to cool theme
setTheme('cool');

// Get all available themes
Object.keys(availableThemes); // ['warm', 'cool', 'classic']
```

### `useCurrentTheme()`
Get current theme info:
```tsx
const { theme, key } = useCurrentTheme();
console.log(theme.name); // "Warm Professional"
console.log(key); // "warm"
```

## 🎯 Built-in Themes

### Warm Professional (Default)
- **Background**: #F9F3EF (warm off-white)
- **Primary**: #456882 (slate blue)
- **Text**: #1B3C53 (dark navy)
- **Accent**: #D2C1B6 (warm beige)

### Cool Modern  
- Clean blue-gray palette
- Perfect for professional/corporate feel

### Classic
- GitHub-inspired high contrast
- Excellent readability and accessibility

## 🔧 Components

### `<ThemeSwitcher />`
Dropdown to switch between themes:
```tsx
<ThemeSwitcher />
<ThemeSwitcher variant="buttons" />
<ThemeSwitcher showLabel={false} />
```

### `<ThemeButton />`
Theme-aware button component:
```tsx
<ThemeButton variant="primary">Primary Action</ThemeButton>
<ThemeButton variant="secondary">Secondary</ThemeButton>
<ThemeButton variant="outline">Outline</ThemeButton>
```

## ⚡ Performance Notes

- **CSS Variables**: Themes use CSS custom properties for instant switching
- **Automatic Persistence**: Theme preferences saved to localStorage  
- **Zero Bundle Impact**: Only active theme colors loaded
- **Hot Switching**: No page refresh needed

## 🎨 Design Guidelines

### Color Usage
- **Primary**: Main actions, links, focus states
- **Secondary**: Subtle backgrounds, less important actions
- **Foreground**: Body text, icons
- **Muted**: Subtle text, placeholders
- **Accent**: Hover states, selected items

### Consistency
- Always use theme colors instead of hardcoded hex values
- Use semantic color names (`primary`) instead of specific colors (`blue`)
- Test all themes to ensure good contrast ratios

## 🚀 Advanced Usage

### Custom Theme Variants
Create theme variants for special cases:
```typescript
const darkWarmTheme = {
  ...warmTheme,
  name: "Warm Dark",
  colors: {
    ...warmTheme.colors,
    background: "#2D2D2D",
    foreground: "#F9F3EF",
  }
};
```

### Runtime Theme Customization
```tsx
import { applyTheme } from '../styles/themeUtils';

// Apply custom colors on the fly
const customTheme = {
  ...warmTheme,
  colors: { ...warmTheme.colors, primary: "#FF0000" }
};

applyTheme(customTheme);
```

## 🐛 Troubleshooting

### Theme not applying?
- Ensure component is wrapped in `<ThemeProvider>`
- Check that CSS custom properties are supported
- Verify theme exists in `themes` registry

### Colors not updating?
- Use CSS custom properties instead of hardcoded colors
- Check browser dev tools for CSS variable values
- Ensure theme system is properly initialized

---

**Pro Tip**: Use the theme switcher in the header to preview how your changes look across different themes instantly!