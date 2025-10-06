import { useState, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import { Button } from '../../../shared/ui/button';
import { FormField, FormLabel, FormMessage } from '../../../shared/ui/form-field';
import { Input } from '../../../shared/ui/input';

type PasswordStrength = 'weak' | 'medium' | 'strong';

export default function RegisterPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { register } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
    displayName?: string;
    general?: string;
  }>({});
  const [isLoading, setIsLoading] = useState(false);

  const emailInputRef = useRef<HTMLInputElement>(null);
  const displayNameInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);

  const returnTo = location.state?.from || '/';

  const getPasswordStrength = (pwd: string): PasswordStrength | null => {
    if (pwd.length === 0) return null;
    if (pwd.length < 8) return 'weak';
    if (pwd.length < 12) return 'medium';
    return 'strong';
  };

  const passwordStrength = getPasswordStrength(password);

  const getStrengthColor = (strength: PasswordStrength | null) => {
    if (!strength) return '';
    switch (strength) {
      case 'weak':
        return 'text-red-600';
      case 'medium':
        return 'text-yellow-600';
      case 'strong':
        return 'text-green-600';
    }
  };

  const getStrengthLabel = (strength: PasswordStrength | null) => {
    if (!strength) return '';
    switch (strength) {
      case 'weak':
        return 'Weak';
      case 'medium':
        return 'Medium';
      case 'strong':
        return 'Strong';
    }
  };

  const validateForm = (): boolean => {
    const newErrors: {
      email?: string;
      password?: string;
      displayName?: string;
    } = {};

    if (!displayName.trim()) {
      newErrors.displayName = 'Display name is required';
    } else if (displayName.trim().length < 2) {
      newErrors.displayName = 'Display name must be at least 2 characters';
    } else if (displayName.trim().length > 50) {
      newErrors.displayName = 'Display name must not exceed 50 characters';
    }

    if (!email) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    } else if (password.length > 72) {
      newErrors.password = 'Password must not exceed 72 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    if (!validateForm()) {
      // Focus first error field
      if (errors.displayName) {
        displayNameInputRef.current?.focus();
      } else if (errors.email) {
        emailInputRef.current?.focus();
      } else if (errors.password) {
        passwordInputRef.current?.focus();
      }
      return;
    }

    setIsLoading(true);

    try {
      await register(email.toLowerCase(), password, displayName.trim());
      navigate(returnTo, { replace: true });
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.error || 'Failed to create account. Please try again.';
      setErrors({ general: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight">
            Create your account
          </h2>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit} autoComplete="on">
          {errors.general && (
            <div
              role="alert"
              className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
            >
              {errors.general}
            </div>
          )}

          <FormField>
            <FormLabel htmlFor="displayName" required>
              Full Name
            </FormLabel>
            <Input
              ref={displayNameInputRef}
              id="displayName"
              name="displayName"
              type="text"
              autoComplete="name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              disabled={isLoading}
              error={!!errors.displayName}
              placeholder="Your first and last name"
              aria-invalid={!!errors.displayName}
              aria-describedby={errors.displayName ? 'displayName-error' : 'displayName-help'}
            />
            {!errors.displayName && (
              <FormMessage id="displayName-help" variant="muted">
                This name will appear in games and on the ledger
              </FormMessage>
            )}
            {errors.displayName && (
              <FormMessage id="displayName-error" variant="error" role="alert">
                {errors.displayName}
              </FormMessage>
            )}
          </FormField>

          <FormField>
            <FormLabel htmlFor="email" required>
              Email address
            </FormLabel>
            <Input
              ref={emailInputRef}
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              error={!!errors.email}
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? 'email-error' : undefined}
            />
            {errors.email && (
              <FormMessage id="email-error" variant="error" role="alert">
                {errors.email}
              </FormMessage>
            )}
          </FormField>

          <FormField>
            <FormLabel htmlFor="password" required>
              Password
            </FormLabel>
            <Input
              ref={passwordInputRef}
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              error={!!errors.password}
              aria-invalid={!!errors.password}
              aria-describedby={
                errors.password ? 'password-error' : passwordStrength ? 'password-strength' : undefined
              }
            />
            {passwordStrength && !errors.password && (
              <p
                id="password-strength"
                className={`mt-1 text-sm font-medium ${getStrengthColor(passwordStrength)}`}
              >
                Password strength: {getStrengthLabel(passwordStrength)}
              </p>
            )}
            {errors.password && (
              <FormMessage id="password-error" variant="error" role="alert">
                {errors.password}
              </FormMessage>
            )}
            {!errors.password && !passwordStrength && (
              <FormMessage variant="muted">
                Password must be at least 8 characters
              </FormMessage>
            )}
          </FormField>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Creating account...' : 'Sign up'}
          </Button>

          <div className="text-center text-sm">
            <Link
              to="/login"
              state={location.state}
              className="text-primary hover:underline"
            >
              Already have an account? Log in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
