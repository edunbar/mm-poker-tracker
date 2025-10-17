import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { API_BASE_URL } from '../../../config/api';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';
import { Heading, Text } from '../../../shared/ui/typography';
import LiveGameForm from '../components/LiveGameForm';

interface LiveGameData {
  sessionName: string;
  players: Array<{
    name: string;
    buy_in: number;
    cash_out: number;
  }>;
  date?: string;
  gameNumber?: number;
}

export default function LiveGameIngestPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const navigate = useNavigate();
  const { getAdminCode } = useAdminSession();
  const adminCode = getAdminCode(publicCode || '');
  const { title: _title } = useGameTitle(publicCode || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (data: LiveGameData) => {
    if (!publicCode) {
      setError('Public code is missing');
      return;
    }

    if (!adminCode) {
      setError('Admin code is missing. Please log in.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/games/upload_live`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Code': adminCode,
        },
        body: JSON.stringify({
          public_code: publicCode,
          session_name: data.sessionName,
          players: data.players,
          ...(data.date && { date: data.date }),
          ...(data.gameNumber && { gameNumber: data.gameNumber })
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to submit live game');
      }

      setSuccess(`Live game "${data.sessionName}" submitted successfully! Game #${result.game_number || 'auto-assigned'}`);
      
      // Optional: Navigate to summary page after success
      setTimeout(() => {
        navigate(`/summary/${publicCode}`);
      }, 2000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4 md:px-6 lg:px-8">
        <div className="mb-8">
          <Heading variant="h1">Submit Live Game Results</Heading>
          <Text variant="body" color="muted" className="mt-2">
            Enter the results from your live poker game
          </Text>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-destructive/10 border-l-4 border-destructive rounded">
            <Text variant="body" color="destructive" weight="medium">Error</Text>
            <Text variant="body" color="destructive">{error}</Text>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-success/10 border-l-4 border-success rounded">
            <Text variant="body" color="success" weight="medium">Success!</Text>
            <Text variant="body" color="success">{success}</Text>
            <Text variant="bodySmall" color="success" className="mt-1">Redirecting to game summary...</Text>
          </div>
        )}

        <LiveGameForm onSubmit={handleSubmit} isLoading={isLoading} />
      </div>
    </div>
  );
}