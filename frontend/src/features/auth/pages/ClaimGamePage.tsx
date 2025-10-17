import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../../api/client';
import { Button } from '../../../shared/ui/button';
import { FormField, FormLabel, FormMessage } from '../../../shared/ui/form-field';
import { Input } from '../../../shared/ui/input';
import { Heading, Text } from '../../../shared/ui/typography';

export default function ClaimGamePage() {
  const navigate = useNavigate();
  const [adminCode, setAdminCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');

    if (!adminCode.trim()) {
      setError('Admin code is required');
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiClient.post('/api/games/claim', {
        admin_code: adminCode.trim(),
      });

      // Handle 201 (first claim) vs 200 (re-claim/extend)
      if (response.status === 201) {
        setSuccessMessage('Game claimed successfully!');
      } else if (response.status === 200) {
        setSuccessMessage('Game access extended!');
      }

      // Redirect after short delay to show message
      setTimeout(() => {
        navigate('/my-games');
      }, 1500);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('Invalid admin code');
      } else if (err.response?.status === 409) {
        setError('This game is already claimed by another user');
      } else {
        setError(err.response?.data?.error || 'Failed to claim game');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Heading variant="h2" className="mb-2">
            Claim a Game
          </Heading>
          <Text variant="body" color="muted">
            Enter the admin code to claim ownership of a game
          </Text>
        </div>

        {successMessage && (
          <div className="rounded-md bg-green-50 dark:bg-green-900/20 p-4">
            <Text variant="bodySmall" className="text-green-800 dark:text-green-200">
              {successMessage}
            </Text>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div role="alert" className="rounded-md bg-destructive/10 p-3">
              <Text variant="bodySmall" className="text-destructive">
                {error}
              </Text>
            </div>
          )}

          <FormField>
            <FormLabel htmlFor="adminCode" required>
              Admin Code
            </FormLabel>
            <Input
              id="adminCode"
              type="text"
              value={adminCode}
              onChange={(e) => setAdminCode(e.target.value)}
              disabled={isLoading}
              placeholder="Enter admin code"
              autoFocus
            />
            <FormMessage variant="muted">
              The admin code was provided when the game was created
            </FormMessage>
          </FormField>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Claiming...' : 'Claim Game'}
          </Button>
        </form>
      </div>
    </div>
  );
}
