import { useEffect, useState } from 'react';
import { apiClient } from '../../api/client';
import { Text } from './typography';

interface PasswordStrengthResult {
  score: number;
  strength: 'weak' | 'fair' | 'good' | 'strong';
  feedback: string[];
  meets_requirements: boolean;
  details: {
    length: number;
    has_lowercase: boolean;
    has_uppercase: boolean;
    has_numbers: boolean;
    has_special: boolean;
    is_common: boolean;
    has_good_length?: boolean;
    has_repeats?: boolean;
    has_sequences?: boolean;
  };
}

interface PasswordStrengthIndicatorProps {
  password: string;
  showFeedback?: boolean;
  onStrengthChange?: (result: PasswordStrengthResult | null) => void;
}

export function PasswordStrengthIndicator({
  password,
  showFeedback = true,
  onStrengthChange
}: PasswordStrengthIndicatorProps) {
  const [result, setResult] = useState<PasswordStrengthResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Don't check empty passwords
    if (!password || password.length === 0) {
      setResult(null);
      onStrengthChange?.(null);
      return;
    }

    // Debounce password strength check
    const timeoutId = setTimeout(async () => {
      setIsLoading(true);
      try {
        const response = await apiClient.post('/api/auth/password-strength', {
          password
        });
        setResult(response.data);
        onStrengthChange?.(response.data);
      } catch (error) {
        console.error('Failed to check password strength:', error);
        setResult(null);
        onStrengthChange?.(null);
      } finally {
        setIsLoading(false);
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [password, onStrengthChange]);

  if (!password || !result) {
    return null;
  }

  // Determine color based on strength
  const getStrengthColor = (strength: string) => {
    switch (strength) {
      case 'strong':
        return 'bg-green-500';
      case 'good':
        return 'bg-blue-500';
      case 'fair':
        return 'bg-yellow-500';
      case 'weak':
      default:
        return 'bg-red-500';
    }
  };

  const getStrengthTextColor = (strength: string) => {
    switch (strength) {
      case 'strong':
        return 'text-green-700 dark:text-green-400';
      case 'good':
        return 'text-blue-700 dark:text-blue-400';
      case 'fair':
        return 'text-yellow-700 dark:text-yellow-400';
      case 'weak':
      default:
        return 'text-red-700 dark:text-red-400';
    }
  };

  const strengthColor = getStrengthColor(result.strength);
  const strengthTextColor = getStrengthTextColor(result.strength);
  const widthPercentage = result.score;

  return (
    <div className="space-y-2">
      {/* Progress bar */}
      <div className="w-full">
        <div className="flex items-center justify-between mb-1">
          <Text variant="bodySmall" className={strengthTextColor}>
            Password strength: {result.strength.charAt(0).toUpperCase() + result.strength.slice(1)}
          </Text>
          <Text variant="bodySmall" color="muted">
            {result.score}/100
          </Text>
        </div>
        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${strengthColor}`}
            style={{ width: `${widthPercentage}%` }}
          />
        </div>
      </div>

      {/* Requirements checklist */}
      {showFeedback && (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded-full flex items-center justify-center ${result.details.length >= 8 ? 'bg-green-500' : 'bg-muted'}`}>
              {result.details.length >= 8 && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <Text variant="bodySmall" color={result.details.length >= 8 ? 'default' : 'muted'}>
              At least 8 characters
            </Text>
          </div>

          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded-full flex items-center justify-center ${result.details.has_lowercase ? 'bg-green-500' : 'bg-muted'}`}>
              {result.details.has_lowercase && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <Text variant="bodySmall" color={result.details.has_lowercase ? 'default' : 'muted'}>
              Lowercase letter (a-z)
            </Text>
          </div>

          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded-full flex items-center justify-center ${result.details.has_uppercase ? 'bg-green-500' : 'bg-muted'}`}>
              {result.details.has_uppercase && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <Text variant="bodySmall" color={result.details.has_uppercase ? 'default' : 'muted'}>
              Uppercase letter (A-Z)
            </Text>
          </div>

          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded-full flex items-center justify-center ${result.details.has_numbers ? 'bg-green-500' : 'bg-muted'}`}>
              {result.details.has_numbers && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <Text variant="bodySmall" color={result.details.has_numbers ? 'default' : 'muted'}>
              Number (0-9)
            </Text>
          </div>

          {!result.details.is_common && result.feedback.length > 0 && (
            <div className="mt-3 p-3 bg-muted/50 rounded border border-border">
              <Text variant="bodySmall" weight="semibold" className="mb-1">
                Suggestions:
              </Text>
              <ul className="space-y-1">
                {result.feedback.map((message, index) => (
                  <li key={index}>
                    <Text variant="bodySmall" color="muted" className="flex items-start gap-1">
                      <span className="mt-1">•</span>
                      <span>{message}</span>
                    </Text>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.details.is_common && (
            <div className="mt-3 p-3 bg-destructive/10 rounded border border-destructive/20">
              <Text variant="bodySmall" className="text-destructive">
                ⚠️ This is a commonly used password. Please choose something more unique.
              </Text>
            </div>
          )}
        </div>
      )}

      {isLoading && (
        <Text variant="caption" color="muted">
          Checking password strength...
        </Text>
      )}
    </div>
  );
}
