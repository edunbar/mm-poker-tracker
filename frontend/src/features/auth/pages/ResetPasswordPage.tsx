import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '../../../shared/ui/button';
import { FormField, FormLabel, FormMessage } from '../../../shared/ui/form-field';
import { Input } from '../../../shared/ui/input';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<{ newPassword?: string; confirmPassword?: string; general?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState<any>(null);

  // Redirect if no token
  useEffect(() => {
    if (!token) {
      navigate('/forgot-password', { replace: true });
    }
  }, [token, navigate]);

  // Check password strength
  useEffect(() => {
    const checkStrength = async () => {
      if (newPassword.length < 8) {
        setPasswordStrength(null);
        return;
      }

      try {
        const response = await axios.post(`${API_URL}/api/auth/password-strength`, {
          password: newPassword,
        });
        setPasswordStrength(response.data);
      } catch (err) {
        setPasswordStrength(null);
      }
    };

    const debounce = setTimeout(checkStrength, 300);
    return () => clearTimeout(debounce);
  }, [newPassword]);

  const validateForm = (): boolean => {
    const newErrors: { newPassword?: string; confirmPassword?: string } = {};

    if (!newPassword) {
      newErrors.newPassword = 'Password is required';
    } else if (newPassword.length < 8) {
      newErrors.newPassword = 'Password must be at least 8 characters';
    } else if (newPassword.length > 72) {
      newErrors.newPassword = 'Password must not exceed 72 characters';
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (confirmPassword !== newPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      await axios.post(`${API_URL}/api/auth/reset-password`, {
        token,
        new_password: newPassword,
      });

      setIsSuccess(true);

      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login', {
          state: { message: 'Password reset successful. Please log in with your new password.' }
        });
      }, 3000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Failed to reset password. Please try again.';
      setErrors({ general: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const getStrengthColor = (strength: string) => {
    switch (strength) {
      case 'strong':
        return 'text-green-600 dark:text-green-400';
      case 'good':
        return 'text-blue-600 dark:text-blue-400';
      case 'fair':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'weak':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-muted-foreground';
    }
  };

  const getStrengthBgColor = (strength: string) => {
    switch (strength) {
      case 'strong':
        return 'bg-green-500';
      case 'good':
        return 'bg-blue-500';
      case 'fair':
        return 'bg-yellow-500';
      case 'weak':
        return 'bg-red-500';
      default:
        return 'bg-gray-300';
    }
  };

  if (!token) {
    return null;
  }

  if (isSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-8 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <CheckCircle className="h-10 w-10 text-green-600" />
          </div>
          <h2 className="mt-6 text-3xl font-bold tracking-tight">
            Password reset successful!
          </h2>
          <p className="mt-4 text-sm text-muted-foreground">
            Your password has been successfully reset. You will be redirected to the login page in a few seconds.
          </p>
          <Button
            onClick={() => navigate('/login')}
            className="mt-6"
          >
            Go to login
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight">
            Set new password
          </h2>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            Choose a strong password for your account
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {errors.general && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive"
            >
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div>
                {errors.general}
                {errors.general.includes('expired') && (
                  <p className="mt-2">
                    <Link to="/forgot-password" className="underline">
                      Request a new reset link
                    </Link>
                  </p>
                )}
              </div>
            </div>
          )}

          <FormField>
            <FormLabel htmlFor="newPassword" required>
              New password
            </FormLabel>
            <Input
              id="newPassword"
              name="newPassword"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={isLoading}
              error={!!errors.newPassword}
              aria-invalid={!!errors.newPassword}
              aria-describedby={errors.newPassword ? 'newPassword-error' : undefined}
            />
            {errors.newPassword && (
              <FormMessage id="newPassword-error" variant="error" role="alert">
                {errors.newPassword}
              </FormMessage>
            )}

            {/* Password Strength Indicator */}
            {passwordStrength && (
              <div className="mt-2 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Strength:</span>
                  <span className={`font-medium ${getStrengthColor(passwordStrength.strength)}`}>
                    {passwordStrength.strength.charAt(0).toUpperCase() + passwordStrength.strength.slice(1)}
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    className={`h-full transition-all duration-300 ${getStrengthBgColor(passwordStrength.strength)}`}
                    style={{ width: `${passwordStrength.score}%` }}
                  />
                </div>
                {passwordStrength.feedback && passwordStrength.feedback.length > 0 && (
                  <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                    {passwordStrength.feedback.map((msg: string, i: number) => (
                      <li key={i}>{msg}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </FormField>

          <FormField>
            <FormLabel htmlFor="confirmPassword" required>
              Confirm new password
            </FormLabel>
            <Input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={isLoading}
              error={!!errors.confirmPassword}
              aria-invalid={!!errors.confirmPassword}
              aria-describedby={errors.confirmPassword ? 'confirmPassword-error' : undefined}
            />
            {errors.confirmPassword && (
              <FormMessage id="confirmPassword-error" variant="error" role="alert">
                {errors.confirmPassword}
              </FormMessage>
            )}
          </FormField>

          <div className="rounded-md bg-blue-50 p-3 text-xs text-blue-800 dark:bg-blue-900/20 dark:text-blue-200">
            <p className="font-medium">Password requirements:</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li>At least 8 characters long</li>
              <li>Contains uppercase and lowercase letters</li>
              <li>Contains at least one number</li>
              <li>Not a commonly used password</li>
            </ul>
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? 'Resetting password...' : 'Reset password'}
          </Button>

          <div className="text-center text-sm">
            <Link
              to="/login"
              className="text-primary hover:underline"
            >
              Back to login
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
