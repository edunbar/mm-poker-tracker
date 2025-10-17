import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useLiveGameInfo, useParticipants, usePendingTransactions } from '../api/liveGame';
import { AdminParticipantsList } from '../components/AdminParticipantsList';
import { CloseGameModal } from '../components/CloseGameModal';
import { PendingTransactionsList } from '../components/PendingTransactionsList';
import { useLiveGameSSE } from '../hooks/useLiveGameSSE';
import { Button } from '../shared/ui/button';
import { Heading, Text } from '../shared/ui/typography';
import { setActiveLiveGame } from '../utils/liveGameStorage';

export default function LiveGameAdminView() {
  const { publicCode, joinCode } = useParams<{ publicCode: string; joinCode: string }>();
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [gameIsClosed, setGameIsClosed] = useState(false);

  // Fetch live game info first
  const { data: liveGame, isLoading: gameLoading, error: liveGameError } = useLiveGameInfo(joinCode);

  // Disable other queries if game is closed
  const { data: participants = [] } = useParticipants(
    gameIsClosed ? undefined : joinCode
  );
  const { data: pendingTransactions = [] } = usePendingTransactions(
    gameIsClosed ? undefined : joinCode
  );

  // Enable real-time updates via SSE only if game is not closed
  useLiveGameSSE({ joinCode: joinCode!, enabled: !!joinCode && !gameIsClosed });

  // Store live game publicCode in localStorage for sidebar navigation
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

  if (gameLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <Text variant="body" color="muted">Loading...</Text>
        </div>
      </div>
    );
  }

  if (!liveGame) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <Heading variant="h3" className="mb-2">Game Not Found</Heading>
          <Text variant="body" color="muted">
            This live game does not exist or has been closed.
          </Text>
        </div>
      </div>
    );
  }

  const activePlayers = participants.filter(p => p.stats.chipsOnTable > 0).length;
  const totalPot = participants.reduce((sum, p) => sum + p.stats.chipsOnTable, 0);
  const pendingCount = pendingTransactions.length;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Heading variant="h2">🎮 Admin Panel</Heading>
            <Text variant="body" color="muted" className="mt-1">
              Join Code: <span className="font-mono text-foreground">{joinCode}</span>
            </Text>
          </div>
          <Button
            variant="destructive"
            onClick={() => setShowCloseModal(true)}
            disabled={liveGame.status === 'closed'}
          >
            Close Game
          </Button>
        </div>

        {/* Game Status Card */}
        <div className="bg-card rounded-lg border border-border p-6">
          <Heading variant="h4" className="mb-4">Game Status</Heading>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <Text variant="caption" color="muted">Status</Text>
              <div className="mt-1">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  liveGame.status === 'active'
                    ? 'bg-success/20 text-success'
                    : 'bg-muted text-muted-foreground'
                }`}>
                  {liveGame.status === 'active' ? '🟢 Active' : '⚫ Closed'}
                </span>
              </div>
            </div>
            <div>
              <Text variant="caption" color="muted">Active Players</Text>
              <Heading variant="h4" className="mt-1">{activePlayers}</Heading>
            </div>
            <div>
              <Text variant="caption" color="muted">Total Pot</Text>
              <Heading variant="h4" className="mt-1">${totalPot.toFixed(2)}</Heading>
            </div>
            <div>
              <Text variant="caption" color="muted">Pending Requests</Text>
              <Heading variant="h4" className="mt-1">
                {pendingCount > 0 ? (
                  <span className="text-warning">{pendingCount}</span>
                ) : (
                  pendingCount
                )}
              </Heading>
            </div>
          </div>
        </div>

        {/* Pending Transactions */}
        {pendingCount > 0 && (
          <div className="bg-card rounded-lg border border-warning/50 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Heading variant="h4">⏳ Pending Approvals</Heading>
              <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-warning/20 text-warning text-xs font-bold">
                {pendingCount}
              </span>
            </div>
            <PendingTransactionsList
              joinCode={joinCode!}
              transactions={pendingTransactions}
              participants={participants}
            />
          </div>
        )}

        {/* Participants */}
        <div className="bg-card rounded-lg border border-border p-6">
          <Heading variant="h4" className="mb-4">
            Players ({participants.length})
          </Heading>
          <AdminParticipantsList
            participants={participants}
          />
        </div>

        {/* Game Info */}
        <div className="bg-card rounded-lg border border-border p-6">
          <Heading variant="h4" className="mb-4">Game Settings</Heading>
          <div className="grid grid-cols-2 gap-4">
            {liveGame.smallBlind && (
              <div>
                <Text variant="caption" color="muted">Small Blind</Text>
                <Text variant="body" weight="medium" className="mt-1">
                  ${liveGame.smallBlind.toFixed(2)}
                </Text>
              </div>
            )}
            {liveGame.bigBlind && (
              <div>
                <Text variant="caption" color="muted">Big Blind</Text>
                <Text variant="body" weight="medium" className="mt-1">
                  ${liveGame.bigBlind.toFixed(2)}
                </Text>
              </div>
            )}
            <div>
              <Text variant="caption" color="muted">Min Buy-In</Text>
              <Text variant="body" weight="medium" className="mt-1">
                ${liveGame.minBuyIn.toFixed(2)}
              </Text>
            </div>
            <div>
              <Text variant="caption" color="muted">Max Buy-In</Text>
              <Text variant="body" weight="medium" className="mt-1">
                {liveGame.maxBuyIn ? `$${liveGame.maxBuyIn.toFixed(2)}` : 'No limit'}
              </Text>
            </div>
          </div>
        </div>

        {/* Share Section */}
        <div className="bg-primary/10 border border-primary/30 rounded-lg p-6">
          <Heading variant="h4" className="mb-2">Share with Players</Heading>
          <Text variant="body" color="muted" className="mb-4">
            Players can join at: {window.location.origin}/join-live/{joinCode}
          </Text>
          <Button
            variant="outline"
            onClick={() => {
              navigator.clipboard.writeText(`${window.location.origin}/join-live/${joinCode}`);
            }}
          >
            Copy Join Link
          </Button>
        </div>
      </div>

      {/* Close Game Modal */}
      {showCloseModal && (
        <CloseGameModal
          joinCode={joinCode!}
          publicCode={liveGame.publicCode!}
          participants={participants}
          onClose={() => setShowCloseModal(false)}
          onSuccess={() => {
            setShowCloseModal(false);
          }}
        />
      )}
    </div>
  );
}
