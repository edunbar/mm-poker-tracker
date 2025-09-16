// Theme Switcher Component
// Allows users to easily switch between available themes

import { Check, ChevronDown, Palette } from 'lucide-react';
import { useState } from 'react';
import { useThemeSwitcher } from '../../contexts/ThemeContext';

interface ThemeSwitcherProps {
  className?: string;
  showLabel?: boolean;
  variant?: 'dropdown' | 'buttons';
}

export function ThemeSwitcher({ 
  className = '', 
  showLabel = true,
  variant = 'dropdown' 
}: ThemeSwitcherProps) {
  const { setTheme, availableThemes, currentTheme } = useThemeSwitcher();
  const [isOpen, setIsOpen] = useState(false);

  if (variant === 'buttons') {
    return (
      <div className={`flex flex-wrap gap-2 ${className}`}>
        {showLabel && (
          <span className="text-sm font-medium text-foreground mr-2 flex items-center">
            <Palette className="w-4 h-4 mr-1" />
            Theme:
          </span>
        )}
        {Object.entries(availableThemes).map(([key, theme]) => (
          <button
            key={key}
            onClick={() => setTheme(key as any)}
            className={`
              px-3 py-1.5 text-xs font-medium rounded-md transition-colors duration-150
              ${currentTheme === key 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              }
            `}
          >
            {theme.name}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center px-3 py-2 text-sm font-medium text-foreground bg-muted hover:bg-accent rounded-md transition-colors duration-150"
      >
        <Palette className="w-4 h-4 mr-2" />
        {showLabel && <span className="mr-2">Theme:</span>}
        <span>{availableThemes[currentTheme].name}</span>
        <ChevronDown className={`w-4 h-4 ml-2 transition-transform duration-150 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute right-0 top-full mt-1 bg-card border border-border rounded-md shadow-lg z-20 min-w-48">
            <div className="py-1">
              {Object.entries(availableThemes).map(([key, theme]) => (
                <button
                  key={key}
                  onClick={() => {
                    setTheme(key as any);
                    setIsOpen(false);
                  }}
                  className={`
                    w-full flex items-center px-3 py-2 text-sm transition-colors duration-150
                    ${currentTheme === key 
                      ? 'bg-accent text-accent-foreground' 
                      : 'text-card-foreground hover:bg-accent hover:text-accent-foreground'
                    }
                  `}
                >
                  <div className="flex-1 text-left">
                    <div className="font-medium">{theme.name}</div>
                    <div className="text-xs text-muted-foreground">{theme.description}</div>
                  </div>
                  {currentTheme === key && (
                    <Check className="w-4 h-4 ml-2" />
                  )}
                </button>
              ))}
            </div>
            
            <div className="border-t border-border px-3 py-2">
              <p className="text-xs text-muted-foreground">
                Theme changes are saved automatically
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Usage examples:
// <ThemeSwitcher />
// <ThemeSwitcher variant="buttons" />
// <ThemeSwitcher showLabel={false} className="ml-auto" />