import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLiveGameInfo, useJoinLiveGame, useClaimAndJoinLiveGame } from '../api/liveGame';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../shared/ui/button';
import { Heading, Text } from '../shared/ui/typography';
import { PlayerClaimingScreen } from '../components/PlayerClaimingScreen';
import type { AvailablePlayer } from '../types/liveGame';

export default function JoinLiveGamePage() {
  const { joinCode } = useParams<{ joinCode: string }>();
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const { showSuccess } = useToast();

  const { data: liveGame, isLoading, error } = useLiveGameInfo(joinCode);
  const joinMutation = useJoinLiveGame();
  const claimAndJoinMutation = useClaimAndJoinLiveGame();

  // State for player claiming flow
  const [showClaimingScreen, setShowClaimingScreen] = useState(false);
  const [availablePlayers, setAvailablePlayers] = useState<AvailablePlayer[]>([]);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!joinCode || !user?.displayName) return;

    try {
      const response = await joinMutation.mutateAsync({
        joinCode,
        displayName: user.displayName
      });

      // Handle different response variants
      if (response.alreadyJoined) {
        // User already joined - just navigate
        showSuccess('Already Joined', 'You have already joined this game');
        navigate(`/live-game/${liveGame!.publicCode}/${joinCode}`);
        return;
      }

      if (response.autoLinked && response.player) {
        // User was auto-linked to existing claimed player
        showSuccess(
          'Welcome Back!',
          `You've been linked to ${response.player.name}`
        );
        navigate(`/live-game/${liveGame!.publicCode}/${joinCode}`);
        return;
      }

      if (response.needsClaim && response.availablePlayers) {
        // User needs to claim a player identity
        setAvailablePlayers(response.availablePlayers);
        setShowClaimingScreen(true);
        return;
      }

      // Default/legacy behavior - direct join successful
      navigate(`/live-game/${liveGame!.publicCode}/${joinCode}`);
    } catch (error: any) {
      // Error handled by mutation
      console.error('Failed to join:', error);
    }
  };

  const handleClaimExisting = async (playerId: string, displayName: string) => {
    if (!joinCode) return;

    try {
      const response = await claimAndJoinMutation.mutateAsync({
        joinCode,
        data: {
          playerId,
          displayName,
        },
      });

      if (response.player) {
        showSuccess(
          'Identity Claimed!',
          `You've been linked to ${response.player.name}`
        );
      }

      navigate(`/live-game/${liveGame!.publicCode}/${joinCode}`);
    } catch (error: any) {
      // Error is shown via mutation error handling
      console.error('Failed to claim and join:', error);
    }
  };

  const handleCreateNew = async (newPlayerName: string, displayName: string) => {
    if (!joinCode) return;

    try {
      const response = await claimAndJoinMutation.mutateAsync({
        joinCode,
        data: {
          newPlayerName,
          displayName,
        },
      });

      if (response.player) {
        showSuccess(
          'Player Created!',
          `New player ${response.player.name} has been created`
        );
      }

      navigate(`/live-game/${liveGame!.publicCode}/${joinCode}`);
    } catch (error: any) {
      // Error is shown via mutation error handling
      console.error('Failed to create and join:', error);
    }
  };

  const handleCancelClaiming = () => {
    setShowClaimingScreen(false);
    setAvailablePlayers([]);
    // User can try joining again or navigate away
  };

  if (isAuthLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <Text variant="body" color="muted">Loading...</Text>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-md text-center space-y-4">
          <Heading variant="h2">Login Required</Heading>
          <Text variant="body" color="muted">
            You must be logged in to join a live game.
          </Text>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => navigate('/login')}>Log In</Button>
            <Button variant="outline" onClick={() => navigate('/register')}>
              Sign Up
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <Text variant="body" color="muted">Loading game...</Text>
        </div>
      </div>
    );
  }

  if (error || !liveGame) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-md text-center space-y-4">
          <Heading variant="h2">Game Not Found</Heading>
          <Text variant="body" color="muted">
            This game code is invalid or the game has ended.
          </Text>
          <Button onClick={() => navigate('/')}>Go Home</Button>
        </div>
      </div>
    );
  }

  // Show claiming screen if needed
  if (showClaimingScreen) {
    return (
      <PlayerClaimingScreen
        availablePlayers={availablePlayers}
        defaultDisplayName={user?.displayName || ''}
        onClaimExisting={handleClaimExisting}
        onCreateNew={handleCreateNew}
        onCancel={handleCancelClaiming}
        isLoading={claimAndJoinMutation.isLoading}
      />
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Heading variant="h2">Join Live Game</Heading>
          <Text variant="body" color="muted" className="mt-2">
            Code: <span className="font-mono text-foreground">{joinCode}</span>
          </Text>
        </div>

        <div className="bg-card rounded-lg border border-border p-8">
          {liveGame.smallBlind && liveGame.bigBlind && (
            <div className="mb-6 text-center">
              <Text variant="bodySmall" color="muted">Blinds</Text>
              <Heading variant="h4" className="mt-1">
                ${liveGame.smallBlind} / ${liveGame.bigBlind}
              </Heading>
            </div>
          )}

          <form onSubmit={handleJoin} className="space-y-6">
            <>
              <div className="bg-muted rounded-lg p-4">
                <Text variant="bodySmall" color="muted" className="mb-2">
                  Playing as
                </Text>
                <Text variant="body" weight="medium">
                  {user?.displayName}
                </Text>
              </div>

              <div className="bg-muted rounded-lg p-4">
                <Text variant="bodySmall" color="muted" className="mb-2">
                  Buy-in Range
                </Text>
                <Text variant="body" weight="medium">
                  ${liveGame.minBuyIn}
                  {liveGame.maxBuyIn && ` - $${liveGame.maxBuyIn}`}
                  {!liveGame.maxBuyIn && '+'}
                </Text>
              </div>

              {joinMutation.error && (
                <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-4">
                  <Text variant="bodySmall" className="text-destructive">
                    {(joinMutation.error as any)?.response?.data?.error ||
                     'Failed to join game. Please try again.'}
                  </Text>
                </div>
              )}

              {claimAndJoinMutation.error && (
                <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-4">
                  <Text variant="bodySmall" className="text-destructive">
                    {(claimAndJoinMutation.error as any)?.response?.data?.error ||
                     'Failed to claim player identity. Please try again.'}
                  </Text>
                </div>
              )}

              <Button
                type="submit"
                className="w-full"
                disabled={joinMutation.isLoading}
              >
                {joinMutation.isLoading ? 'Joining...' : 'Join Game'}
              </Button>
            </>
          </form>
        </div>
      </div>
    </div>
  );
}
