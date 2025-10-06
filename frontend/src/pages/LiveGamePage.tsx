import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useGameInfo } from '../api/game';
import { useActiveLiveGameByPublicCode } from '../api/liveGame';
import { CreateLiveGameModal } from '../components/CreateLiveGameModal';
import { LiveGameCreatedModal } from '../components/LiveGameCreatedModal';
import { Heading, Text } from '../shared/ui/typography';
import { Button } from '../shared/ui/button';

export default function LiveGamePage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const navigate = useNavigate();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createdGame, setCreatedGame] = useState<{ joinCode: string; liveGameId: string } | null>(null);

  // Fetch game info to get gameId
  const { data: gameInfo, isLoading: isLoadingGame, error: gameError } = useGameInfo(publicCode);

  // Check for active live game
  const { data: activeLiveGame, isLoading: isLoadingLiveGame, error: liveGameError } = useActiveLiveGameByPublicCode(publicCode);

  // Redirect to admin view if there's an active live game
  useEffect(() => {
    if (activeLiveGame?.joinCode && publicCode) {
      navigate(`/live/${publicCode}/${activeLiveGame.joinCode}/admin`);
    }
  }, [activeLiveGame, publicCode, navigate]);

  const handleCreateSuccess = (joinCode: string, liveGameId: string) => {
    setShowCreateModal(false);
    setCreatedGame({ joinCode, liveGameId });
  };

  const handleCreatedModalClose = () => {
    if (createdGame && publicCode) {
      navigate(`/live/${publicCode}/${createdGame.joinCode}/admin`);
    }
  };

  // Loading state
  if (isLoadingGame || isLoadingLiveGame) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <Text variant="body" color="muted">Loading...</Text>
        </div>
      </div>
    );
  }

  // Error state - game not found
  if (gameError || !gameInfo) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-md text-center space-y-4">
          <Heading variant="h2">Game Not Found</Heading>
          <Text variant="body" color="muted">
            This game code is invalid or does not exist.
          </Text>
          <Button onClick={() => navigate('/')}>Go Home</Button>
        </div>
      </div>
    );
  }

  // Error state - failed to check for active live game
  if (liveGameError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-md text-center space-y-4">
          <Heading variant="h2">Error</Heading>
          <Text variant="body" color="muted">
            Failed to check for active live game. Please try again.
          </Text>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  // No active live game - show create option
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Heading variant="h2">Live Game</Heading>
          {gameInfo.title && (
            <Text variant="body" color="muted" className="mt-2">
              {gameInfo.title}
            </Text>
          )}
          <Text variant="bodySmall" color="muted" className="mt-1">
            Code: <span className="font-mono text-foreground">{publicCode}</span>
          </Text>
        </div>

        <div className="bg-card rounded-lg border border-border p-8 space-y-6">
          <div className="text-center">
            <Heading variant="h4" className="mb-2">No Active Live Game</Heading>
            <Text variant="body" color="muted">
              Start a new live game session to track real-time buy-ins and cash-outs.
            </Text>
          </div>

          <Button
            onClick={() => setShowCreateModal(true)}
            className="w-full"
            size="lg"
          >
            Start New Live Game
          </Button>

          <div className="bg-muted rounded-lg p-4">
            <Text variant="bodySmall" color="muted">
              Live games allow you to track player buy-ins and cash-outs in real-time
              during an active poker session. Players can join using a shared code and
              request transactions from their phones.
            </Text>
          </div>
        </div>
      </div>

      {showCreateModal && gameInfo && (
        <CreateLiveGameModal
          gameId={gameInfo.gameId}
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleCreateSuccess}
        />
      )}

      {createdGame && publicCode && (
        <LiveGameCreatedModal
          joinCode={createdGame.joinCode}
          liveGameId={createdGame.liveGameId}
          publicCode={publicCode}
          onClose={handleCreatedModalClose}
        />
      )}
    </div>
  );
}
