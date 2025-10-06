import { Plus } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../../../api/client';
import { Button } from '../../../shared/ui/button';
import { Heading, Text } from '../../../shared/ui/typography';

interface Game {
  id: string;
  title: string;
  public_code: string;
  admin_code_expires_at: string | null;
  created_at: string;
  session_count: number;
}

export default function MyGamesPage() {
  const [games, setGames] = useState<Game[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchGames();
  }, []);

  const fetchGames = async () => {
    try {
      const response = await apiClient.get('/api/games/me');
      setGames(response.data.games);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load games');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto" />
          <Text variant="body" color="muted" className="mt-4">
            Loading your games...
          </Text>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Text variant="body" className="text-destructive">
            {error}
          </Text>
          <Button onClick={fetchGames} variant="outline" className="mt-4">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  if (games.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center max-w-md">
          <Heading variant="h3" className="mb-4">
            No games claimed yet
          </Heading>
          <Text variant="body" color="muted" className="mb-6">
            Claim your first game using the admin code provided when the game was created.
          </Text>
          <Link to="/claim-game">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Claim Your First Game
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Heading variant="h2">My Games</Heading>
        <Link to="/claim-game">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Claim Game
          </Button>
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4">
                <Text variant="bodySmall" weight="semibold">Game</Text>
              </th>
              <th className="text-left py-3 px-4">
                <Text variant="bodySmall" weight="semibold">Public Code</Text>
              </th>
              <th className="text-left py-3 px-4">
                <Text variant="bodySmall" weight="semibold">Sessions</Text>
              </th>
              <th className="text-left py-3 px-4">
                <Text variant="bodySmall" weight="semibold">Created</Text>
              </th>
              <th className="text-left py-3 px-4">
                <Text variant="bodySmall" weight="semibold">Actions</Text>
              </th>
            </tr>
          </thead>
          <tbody>
            {games.map((game) => (
              <tr key={game.id} className="border-b border-border hover:bg-muted/50">
                <td className="py-3 px-4">
                  <Text variant="body">{game.title || 'Untitled Game'}</Text>
                </td>
                <td className="py-3 px-4">
                  <Text variant="body" className="font-mono">
                    {game.public_code}
                  </Text>
                </td>
                <td className="py-3 px-4">
                  <Text variant="body">{game.session_count}</Text>
                </td>
                <td className="py-3 px-4">
                  <Text variant="bodySmall" color="muted">
                    {new Date(game.created_at).toLocaleDateString()}
                  </Text>
                </td>
                <td className="py-3 px-4">
                  <div className="flex gap-2">
                    <Link to={`/summary/${game.public_code}`}>
                      <Button variant="outline" size="sm">
                        View
                      </Button>
                    </Link>
                    <Link to={`/ingest/${game.public_code}`}>
                      <Button variant="outline" size="sm">
                        Upload
                      </Button>
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
