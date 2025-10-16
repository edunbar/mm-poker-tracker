import axios from 'axios';
import { CheckCircle } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../../shared/ui/button';
import { FormField, FormLabel, FormMessage } from '../../../shared/ui/form-field';
import { Input } from '../../../shared/ui/input';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const validateEmail = (email: string): boolean => {
    if (!email) {
      setError('Email is required');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validateEmail(email)) {
      return;
    }

    setIsLoading(true);

    try {
      await axios.post(`${API_URL}/api/auth/forgot-password`, {
        email: email.toLowerCase(),
      });

      // Always show success (server doesn't reveal if email exists)
      setIsSuccess(true);
    } catch (err: any) {
      // Even on error, show success message (prevent email enumeration)
      setIsSuccess(true);
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-10 w-10 text-green-600" />
            </div>
            <h2 className="mt-6 text-3xl font-bold tracking-tight">
              Check your email
            </h2>
            <p className="mt-4 text-sm text-muted-foreground">
              If an account exists with <strong>{email}</strong>, you will receive password reset instructions shortly.
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              The reset link will expire in 24 hours.
            </p>
          </div>

          <div className="rounded-md bg-blue-50 p-4 text-sm text-blue-800 dark:bg-blue-900/20 dark:text-blue-200">
            <p className="font-medium">Didn't receive an email?</p>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>Check your spam folder</li>
              <li>Make sure you entered the correct email</li>
              <li>Wait a few minutes for the email to arrive</li>
              <li>You can request another reset after 1 hour</li>
            </ul>
          </div>

          <div className="text-center">
            <Link
              to="/login"
              className="text-primary hover:underline"
            >
              Back to login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight">
            Reset your password
          </h2>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            Enter your email address and we'll send you a link to reset your password.
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div
              role="alert"
              className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
            >
              {error}
            </div>
          )}

          <FormField>
            <FormLabel htmlFor="email" required>
              Email address
            </FormLabel>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              error={!!error}
              aria-invalid={!!error}
              aria-describedby={error ? 'email-error' : undefined}
              placeholder="you@example.com"
            />
            {error && (
              <FormMessage id="email-error" variant="error" role="alert">
                {error}
              </FormMessage>
            )}
          </FormField>

          <div className="rounded-md bg-yellow-50 p-3 text-xs text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-200">
            <p>
              <strong>Rate limit:</strong> You can request a password reset up to 3 times per hour.
            </p>
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? 'Sending...' : 'Send reset link'}
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
