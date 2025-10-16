import { Plus, Eye, X, Check } from 'lucide-react';
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { apiClient } from '../../../api/client';
import { Button } from '../../../shared/ui/button';
import { Heading, Text, Code } from '../../../shared/ui/typography';

interface Game {
  id: string;
  title: string;
  public_code: string;
  admin_code?: string; // Only present for games owned by current user
  admin_code_expires_at: string | null;
  created_at: string;
  session_count: number;
}

export default function MyGamesPage() {

  const [games, setGames] = useState<Game[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedAdminCode, setSelectedAdminCode] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  useEffect(() => {
    fetchGames();
  }, []);

  // Reset copy state when modal opens/closes
  useEffect(() => {
    setIsCopied(false);
  }, [selectedAdminCode]);

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
            No games yet
          </Heading>
          <Text variant="body" color="muted" className="mb-6">
            Create a new game or claim an existing one using an admin code.
          </Text>
          <div className="flex gap-2 justify-center">
            <Link to="/create-game">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Game
              </Button>
            </Link>
            <Link to="/claim-game">
              <Button variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Claim Game
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Heading variant="h2">My Games</Heading>
        <div className="flex gap-2">
          <Link to="/create-game">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Game
            </Button>
          </Link>
          <Link to="/claim-game">
            <Button variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              Claim Game
            </Button>
          </Link>
        </div>
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
                    {game.admin_code && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedAdminCode(game.admin_code!)}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        Admin
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Admin Code Modal */}
      {selectedAdminCode && createPortal(
        <div
          className="fixed inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-[9999]"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setSelectedAdminCode(null);
            }
          }}
        >
          <div
            className="bg-popover text-popover-foreground rounded-lg shadow-xl border border-border max-w-md w-full mx-4 p-6 relative z-[10000]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <Heading variant="h3">Admin Code</Heading>
              <button onClick={() => setSelectedAdminCode(null)} className="text-muted-foreground hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-4 bg-warning/10 rounded border border-warning/20 mb-4">
              <Text variant="bodySmall" weight="semibold" className="mb-2">Admin Code</Text>
              <div className="flex items-center gap-2">
                <Code className="font-mono text-xs break-all flex-1">{selectedAdminCode}</Code>
                <Button
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(selectedAdminCode);
                    setIsCopied(true);
                    setTimeout(() => setIsCopied(false), 2000);
                  }}
                >
                  {isCopied ? (
                    <>
                      <Check className="h-4 w-4 mr-1" />
                      Copied!
                    </>
                  ) : (
                    'Copy'
                  )}
                </Button>
              </div>
              <Text variant="caption" color="muted" className="mt-2">
                Use this code for game management and session uploads
              </Text>
            </div>

            <Button onClick={() => setSelectedAdminCode(null)} className="w-full">
              Close
            </Button>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
