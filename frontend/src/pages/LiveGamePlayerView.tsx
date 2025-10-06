import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLiveGameInfo, useParticipants } from '../api/liveGame';
import { useLiveGameSSE } from '../hooks/useLiveGameSSE';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../shared/ui/button';
import { Heading, Text } from '../shared/ui/typography';
import { BuyInModal } from '../components/BuyInModal';
import { CashOutModal } from '../components/CashOutModal';
import { PlayerStats } from '../components/PlayerStats';
import { setActiveLiveGame, clearActiveLiveGame } from '../utils/liveGameStorage';

export default function LiveGamePlayerView() {
  const { publicCode, joinCode } = useParams<{ publicCode: string; joinCode: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [showBuyInModal, setShowBuyInModal] = useState(false);
  const [showCashOutModal, setShowCashOutModal] = useState(false);
  const [gameIsClosed, setGameIsClosed] = useState(false);

  const { data: liveGame, error: liveGameError, isLoading: liveGameLoading } = useLiveGameInfo(joinCode);

  // Disable participants query if game is closed or has error
  const { data: participants = [] } = useParticipants(
    gameIsClosed ? undefined : joinCode
  );

  // Enable real-time updates via SSE only if game is not closed
  useLiveGameSSE({ joinCode: joinCode!, enabled: !!joinCode && !gameIsClosed });

  // Find current user's participant data
  const myParticipant = participants.find(p => p.userId === user?.id);
  const canCashOut = myParticipant && myParticipant.stats.chipsOnTable > 0;

  // Store active live game in localStorage for sidebar navigation
  useEffect(() => {
    if (publicCode && joinCode) {
      setActiveLiveGame(joinCode, publicCode);
    }
  }, [publicCode, joinCode]);

  // Detect when game is closed and disable queries
  useEffect(() => {
    if (liveGame?.status === 'closed') {
      setGameIsClosed(true);
    }
  }, [liveGame?.status]);

  // Detect when game has error (404/410) and disable queries
  useEffect(() => {
    if (liveGameError) {
      const error = liveGameError as any;
      const is404or410 = error?.response?.status === 404 || error?.response?.status === 410;
      if (is404or410) {
        setGameIsClosed(true);
      }
    }
  }, [liveGameError]);

  // Redirect to game summary if game is closed
  useEffect(() => {
    if (liveGame?.status === 'closed' && publicCode) {
      // Clear active game and redirect to summary page
      clearActiveLiveGame();
      navigate(`/${publicCode}`, { replace: true });
    }
  }, [liveGame?.status, publicCode, navigate]);

  // Clear active live game from sidebar when game has ended (404/410 errors)
  useEffect(() => {
    if (liveGameError) {
      const error = liveGameError as any;
      const is404or410 = error?.response?.status === 404 || error?.response?.status === 410;
      if (is404or410) {
        clearActiveLiveGame();
      }
    }
  }, [liveGameError]);

  // Handle API errors (game not found, closed, or server error)
  if (liveGameError) {
    const error = liveGameError as any;
    const is404or410 = error?.response?.status === 404 || error?.response?.status === 410;

    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <span className="text-4xl">🎮</span>
          </div>

          <div className="space-y-2">
            <Heading variant="h3">
              {is404or410 ? 'Game Has Ended' : 'Unable to Load Game'}
            </Heading>
            <Text variant="body" color="muted">
              {is404or410
                ? 'This live game has been closed by the host. Check the game summary for final results.'
                : 'We encountered an error loading this game. Please try again or contact support.'}
            </Text>
          </div>

          <div className="flex flex-col gap-3">
            <Button
              onClick={() => navigate('/my-games')}
              className="w-full"
            >
              Return to My Games
            </Button>
            <Button
              variant="outline"
              onClick={() => window.location.reload()}
              className="w-full"
            >
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Show loading state
  if (liveGameLoading || !liveGame || !myParticipant) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <Text variant="body" color="muted">Loading...</Text>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <Heading variant="h2">🎮 Live Game</Heading>
          <Text variant="body" color="muted" className="mt-1">
            Code: <span className="font-mono text-foreground">{joinCode}</span>
          </Text>
          <Text variant="bodySmall" color="muted">
            Playing as: {myParticipant.displayName}
          </Text>
        </div>

        {/* Player Stats Card */}
        <PlayerStats participant={myParticipant} />

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <Button
            size="lg"
            onClick={() => setShowBuyInModal(true)}
            className="h-16"
          >
            💵 Buy In
          </Button>
          <Button
            size="lg"
            variant="outline"
            onClick={() => setShowCashOutModal(true)}
            disabled={!canCashOut}
            className="h-16"
          >
            🚪 Cash Out
          </Button>
        </div>

        {!canCashOut && (
          <Text variant="caption" color="muted" className="text-center block">
            You must buy in before you can cash out
          </Text>
        )}
      </div>

      {/* Modals */}
      {showBuyInModal && liveGame && (
        <BuyInModal
          joinCode={joinCode!}
          minBuyIn={liveGame.minBuyIn}
          maxBuyIn={liveGame.maxBuyIn}
          onClose={() => setShowBuyInModal(false)}
        />
      )}

      {showCashOutModal && myParticipant && (
        <CashOutModal
          joinCode={joinCode!}
          chipsOnTable={myParticipant.stats.chipsOnTable}
          totalBuyIns={myParticipant.stats.totalBuyIns}
          onClose={() => setShowCashOutModal(false)}
        />
      )}
    </div>
  );
}
