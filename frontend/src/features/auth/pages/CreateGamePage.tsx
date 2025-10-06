import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { apiClient } from '../../../api/client';
import { Button } from '../../../shared/ui/button';
import { FormField, FormLabel } from '../../../shared/ui/form-field';
import { Input } from '../../../shared/ui/input';
import { Heading, Text, Code } from '../../../shared/ui/typography';

export default function CreateGamePage() {
  const navigate = useNavigate();
  const [newGameTitle, setNewGameTitle] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createdGame, setCreatedGame] = useState<{
    public_code: string;
    admin_code: string;
    title?: string;
  } | null>(null);

  const handleCreateGame = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    setCreateError('');

    try {
      // Create the game
      const createResponse = await apiClient.post('/api/games/create', {
        title: newGameTitle.trim() || undefined
      });

      const gameData = createResponse.data;

      // Automatically claim the game
      await apiClient.post('/api/games/claim', {
        admin_code: gameData.admin_code
      });

      // Show success screen
      setCreatedGame(gameData);

    } catch (err: any) {
      setCreateError(err.response?.data?.error || 'Failed to create game');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDone = () => {
    navigate('/my-games');
  };

  if (createdGame) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <div className="bg-card rounded-lg border border-border p-8">
          <Heading variant="h2" className="mb-4">Game Created!</Heading>
          <Text variant="body" color="muted" className="mb-6">
            Your game has been created and automatically added to your games.
          </Text>

          <div className="space-y-4 mb-6">
            <div className="p-4 bg-muted rounded">
              <Text variant="bodySmall" weight="semibold" className="mb-2">Public Code</Text>
              <div className="flex items-center gap-2">
                <Code className="font-mono flex-1 text-lg">{createdGame.public_code}</Code>
                <Button
                  size="sm"
                  onClick={() => navigator.clipboard.writeText(createdGame.public_code)}
                >
                  Copy
                </Button>
              </div>
              <Text variant="caption" color="muted" className="mt-2">
                Share this code with players to view game summaries
              </Text>
            </div>

            <div className="p-4 bg-warning/10 rounded border border-warning/20">
              <Text variant="bodySmall" weight="semibold" className="mb-2">Admin Code</Text>
              <div className="flex items-center gap-2">
                <Code className="font-mono text-xs break-all flex-1">{createdGame.admin_code}</Code>
                <Button
                  size="sm"
                  onClick={() => navigator.clipboard.writeText(createdGame.admin_code)}
                >
                  Copy
                </Button>
              </div>
              <Text variant="caption" color="muted" className="mt-2">
                ⚠️ Save this code! You'll need it for game management and session uploads.
              </Text>
            </div>
          </div>

          <Button onClick={handleDone} className="w-full">
            Go to My Games
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8">
      <Link to="/my-games" className="inline-flex items-center text-primary hover:underline mb-6">
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to My Games
      </Link>

      <div className="bg-card rounded-lg border border-border p-8">
        <Heading variant="h2" className="mb-2">Create New Game</Heading>
        <Text variant="body" color="muted" className="mb-6">
          Create a new poker game to track sessions and manage your home game.
        </Text>

        <form onSubmit={handleCreateGame} className="space-y-6">
          {createError && (
            <div className="p-4 bg-destructive/10 text-destructive rounded border border-destructive/20">
              <Text variant="bodySmall">{createError}</Text>
            </div>
          )}

          <FormField>
            <FormLabel htmlFor="gameTitle">Game Title (optional)</FormLabel>
            <Input
              id="gameTitle"
              value={newGameTitle}
              onChange={(e) => setNewGameTitle(e.target.value)}
              placeholder="e.g., Friday Night Poker"
              maxLength={100}
              disabled={isCreating}
            />
            <Text variant="caption" color="muted">
              Give your game a memorable name, or leave blank for "Untitled Game"
            </Text>
          </FormField>

          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/my-games')}
              className="flex-1"
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isCreating}
              className="flex-1"
            >
              {isCreating ? 'Creating...' : 'Create Game'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
