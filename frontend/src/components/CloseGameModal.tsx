import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, AlertTriangle, CheckCircle } from 'lucide-react';
import { useCloseLiveGame } from '../api/liveGame';
import { Button } from '../shared/ui/button';
import { Heading, Text } from '../shared/ui/typography';
import type { Participant, UncashedPlayer } from '../types/liveGame';
import { clearActiveLiveGame } from '../utils/liveGameStorage';

interface CloseGameModalProps {
  joinCode: string;
  publicCode: string;
  participants: Participant[];
  onClose: () => void;
  onSuccess: () => void;
}

export function CloseGameModal({
  joinCode,
  publicCode,
  participants,
  onClose,
  onSuccess
}: CloseGameModalProps) {
  const navigate = useNavigate();
  const closeMutation = useCloseLiveGame();
  const [uncashedPlayers, setUncashedPlayers] = useState<UncashedPlayer[]>([]);
  const [confirmedZeroPlayers, setConfirmedZeroPlayers] = useState<Set<string>>(new Set());
  const [showConfirmation, setShowConfirmation] = useState(false);

  const handleFirstAttempt = async () => {
    try {
      // First attempt - try to close without confirmations
      await closeMutation.mutateAsync({ joinCode });

      // Success! Game closed
      clearActiveLiveGame();
      onSuccess();

      // Navigate to game summary page after successful close
      navigate(`/${publicCode}`);
    } catch (error: any) {
      // Check if we got 409 with uncashed players
      if (error.response?.status === 409 && error.response?.data?.uncashed_players) {
        const uncashed = error.response.data.uncashed_players.map((p: any) => ({
          participantId: p.participant_id,
          displayName: p.display_name,
          totalBuyIns: p.total_buy_ins,
          chipsOnTable: p.chips_on_table,
        }));

        setUncashedPlayers(uncashed);
        setShowConfirmation(true);
      } else {
        // Other error - will be displayed by error UI
        console.error('Failed to close game:', error);
      }
    }
  };

  const handleConfirmedClose = async () => {
    try {
      // Second attempt - close with confirmed zero players
      const confirmedIds = Array.from(confirmedZeroPlayers);
      await closeMutation.mutateAsync({
        joinCode,
        confirmedZeroPlayers: confirmedIds,
      });

      // Success! Game closed
      clearActiveLiveGame();
      onSuccess();

      // Navigate to game summary page after successful close
      navigate(`/${publicCode}`);
    } catch (error) {
      console.error('Failed to close game with confirmations:', error);
    }
  };

  const togglePlayer = (participantId: string) => {
    const newSet = new Set(confirmedZeroPlayers);
    if (newSet.has(participantId)) {
      newSet.delete(participantId);
    } else {
      newSet.add(participantId);
    }
    setConfirmedZeroPlayers(newSet);
  };

  const selectAll = () => {
    setConfirmedZeroPlayers(new Set(uncashedPlayers.map(p => p.participantId)));
  };

  const deselectAll = () => {
    setConfirmedZeroPlayers(new Set());
  };

  // Show uncashed players confirmation screen
  if (showConfirmation && uncashedPlayers.length > 0) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-background rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-6 w-6 text-warning" />
              <Heading variant="h4">Players Haven't Cashed Out</Heading>
            </div>
            <Button onClick={onClose} variant="ghost" size="icon-sm">
              <X className="h-6 w-6" />
            </Button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-4 overflow-y-auto flex-1">
            <div className="bg-warning/10 border border-warning/30 rounded-lg p-4">
              <Text variant="bodySmall" className="text-warning">
                The following players haven't cashed out yet. Select any players who left with $0
                (busted) to automatically create $0 cash-outs for them.
              </Text>
            </div>

            {/* Select All / Deselect All */}
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={selectAll}>
                Select All
              </Button>
              <Button variant="outline" size="sm" onClick={deselectAll}>
                Deselect All
              </Button>
            </div>

            {/* Uncashed Players List */}
            <div className="space-y-2">
              {uncashedPlayers.map((player) => {
                const isSelected = confirmedZeroPlayers.has(player.participantId);

                return (
                  <div
                    key={player.participantId}
                    className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-primary/10 border-primary'
                        : 'bg-card border-border hover:border-primary/50'
                    }`}
                    onClick={() => togglePlayer(player.participantId)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                          isSelected
                            ? 'bg-primary border-primary'
                            : 'border-border'
                        }`}>
                          {isSelected && <CheckCircle className="h-4 w-4 text-primary-foreground" />}
                        </div>
                        <div>
                          <Text variant="body" weight="medium">{player.displayName}</Text>
                          <Text variant="caption" color="muted">
                            Buy-ins: ${player.totalBuyIns.toFixed(2)} |
                            Chips on table: ${player.chipsOnTable.toFixed(2)}
                          </Text>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="bg-muted rounded-lg p-4">
              <Text variant="bodySmall" color="muted">
                {confirmedZeroPlayers.size === 0 && (
                  <>You haven't selected any players. The game will remain open if you continue without selections.</>
                )}
                {confirmedZeroPlayers.size > 0 && (
                  <>
                    Selected {confirmedZeroPlayers.size} player{confirmedZeroPlayers.size === 1 ? '' : 's'} to
                    automatically cash out with $0. The game will only close if all remaining players have
                    cashed out normally.
                  </>
                )}
              </Text>
            </div>
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-border">
            <>
              {closeMutation.error && (
                <div className="mb-4 bg-destructive/10 border border-destructive/50 rounded-lg p-4">
                  <Text variant="bodySmall" className="text-destructive">
                    {(closeMutation.error as any)?.response?.data?.error ||
                     'Failed to close game'}
                  </Text>
                </div>
              )}

              <div className="flex gap-3">
                <Button variant="outline" onClick={onClose} className="flex-1">
                  Cancel
                </Button>
                <Button
                  onClick={handleConfirmedClose}
                  disabled={closeMutation.isLoading}
                  className="flex-1"
                >
                  {closeMutation.isLoading ? 'Closing...' : 'Close Game'}
                </Button>
              </div>
            </>
          </div>
        </div>
      </div>
    );
  }

  // Initial close confirmation screen
  const activePlayers = participants.filter(p => p.stats.chipsOnTable > 0).length;
  const totalPot = participants.reduce((sum, p) => sum + p.stats.chipsOnTable, 0);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-md w-full">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <Heading variant="h4">Close Game</Heading>
          <Button onClick={onClose} variant="ghost" size="icon-sm">
            <X className="h-6 w-6" />
          </Button>
        </div>

        <div className="p-6 space-y-6">
          <>
            <div className="bg-warning/10 border border-warning/30 rounded-lg p-4">
              <Text variant="bodySmall" className="text-warning">
                ⚠️ This will end the live game and create a final session in your game ledger.
              </Text>
            </div>

            <div className="bg-muted rounded-lg p-4 space-y-2">
              <div className="flex justify-between">
                <Text variant="bodySmall" color="muted">Active Players:</Text>
                <Text variant="bodySmall" weight="medium">{activePlayers}</Text>
              </div>
              <div className="flex justify-between">
                <Text variant="bodySmall" color="muted">Total Pot:</Text>
                <Text variant="bodySmall" weight="medium">${totalPot.toFixed(2)}</Text>
              </div>
            </div>

            <div className="bg-muted rounded-lg p-4">
              <Text variant="bodySmall" color="muted">
                Make sure all players have cashed out before closing. If any players
                busted out with $0, you'll be able to confirm them in the next step.
              </Text>
            </div>

            {closeMutation.error && (
              <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-4">
                <Text variant="bodySmall" className="text-destructive">
                  {(closeMutation.error as any)?.response?.data?.error ||
                   'Failed to close game'}
                </Text>
              </div>
            )}

            <div className="flex gap-3">
              <Button variant="outline" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleFirstAttempt}
                disabled={closeMutation.isLoading}
                className="flex-1"
              >
                {closeMutation.isLoading ? 'Closing...' : 'Close Game'}
              </Button>
            </div>
          </>
        </div>
      </div>
    </div>
  );
}
