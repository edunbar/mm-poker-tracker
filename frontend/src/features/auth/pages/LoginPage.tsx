import { useState, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import { Button } from '../../../shared/ui/button';
import { FormField, FormLabel, FormMessage } from '../../../shared/ui/form-field';
import { Input } from '../../../shared/ui/input';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; general?: string }>({});
  const [isLoading, setIsLoading] = useState(false);

  const emailInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);

  const returnTo = location.state?.from || '/';

  const validateForm = (): boolean => {
    const newErrors: { email?: string; password?: string } = {};

    if (!email) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 12) {
      newErrors.password = 'Password must be at least 12 characters';
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
      if (errors.email) {
        emailInputRef.current?.focus();
      } else if (errors.password) {
        passwordInputRef.current?.focus();
      }
      return;
    }

    setIsLoading(true);

    try {
      await login(email.toLowerCase(), password, rememberMe);
      navigate(returnTo, { replace: true });
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to log in. Please try again.';
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
            Log in to your account
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
            <FormLabel htmlFor="email" required>
              Email address
            </FormLabel>
            <Input
              ref={emailInputRef}
              id="email"
              name="username"
              type="email"
              autoComplete="username"
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
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              error={!!errors.password}
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'password-error' : undefined}
            />
            {errors.password && (
              <FormMessage id="password-error" variant="error" role="alert">
                {errors.password}
              </FormMessage>
            )}
          </FormField>

          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={isLoading}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm">
                Keep me logged in for 30 days
              </label>
            </div>
            <div className="text-sm">
              <Link to="/forgot-password" className="text-primary hover:underline">
                Forgot password?
              </Link>
            </div>
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? 'Logging in...' : 'Log in'}
          </Button>

          <div className="text-center text-sm">
            <Link
              to="/register"
              state={location.state}
              className="text-primary hover:underline"
            >
              Don't have an account? Sign up
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
