import { Info, X } from 'lucide-react';
import { useState } from 'react';
import {
  useClaimablePlayers,
  usePlayerPreview,
  useClaimPlayer,
} from '../api/playerIdentityClaim';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../shared/ui/button';
import { FormField, FormLabel } from '../shared/ui/form-field';
import { Input } from '../shared/ui/input';
import { Heading, Text } from '../shared/ui/typography';

interface ClaimPlayerModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function ClaimPlayerModal({ onClose, onSuccess }: ClaimPlayerModalProps) {
  const [step, setStep] = useState<'enter-code' | 'select-player' | 'confirm'>('enter-code');
  const [gamePublicCode, setGamePublicCode] = useState('');
  const [gameIdForQuery, setGameIdForQuery] = useState<string | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const { showSuccess, showError } = useToast();

  const { data: claimablePlayers, isLoading: isLoadingPlayers, error: playersError } = useClaimablePlayers(gameIdForQuery);
  const { data: preview, isLoading: isLoadingPreview } = usePlayerPreview(selectedPlayerId);
  const claimMutation = useClaimPlayer();

  const handleGameCodeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const code = gamePublicCode.trim().toUpperCase();

    if (!code) {
      showError('Error', 'Please enter a game public code');
      return;
    }

    // Use the public code as game ID for the query
    setGameIdForQuery(code);
    setStep('select-player');
  };

  const handlePlayerSelect = (playerId: string) => {
    setSelectedPlayerId(playerId);
    setStep('confirm');
  };

  const handleClaim = async () => {
    if (!selectedPlayerId) return;

    try {
      await claimMutation.mutateAsync({
        playerId: selectedPlayerId,
        verificationMethod: 'manual',
      });
      showSuccess('Success', 'Player identity claimed successfully!');
      onSuccess();
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to claim player identity';
      showError('Error', errorMessage);
    }
  };

  const handleBack = () => {
    if (step === 'select-player') {
      setStep('enter-code');
      setGameIdForQuery(null);
    } else if (step === 'confirm') {
      setStep('select-player');
      setSelectedPlayerId(null);
    }
  };

  const handleClose = () => {
    if (!claimMutation.isLoading) {
      onClose();
    }
  };

  const getStepTitle = () => {
    if (step === 'enter-code') return 'Enter Game Code';
    if (step === 'select-player') return 'Select Your Player';
    return 'Confirm Identity';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <Heading variant="h4">{getStepTitle()}</Heading>
          <Button
            onClick={handleClose}
            variant="ghost"
            size="icon-sm"
            disabled={claimMutation.isLoading}
          >
            <X className="h-6 w-6" />
          </Button>
        </div>

        {/* Body */}
        <div className="p-6">
          {/* Step 1: Enter Game Code */}
          {step === 'enter-code' ? (
            <form onSubmit={handleGameCodeSubmit} className="space-y-4">
              <Text variant="body" color="muted" className="mb-4">
                Enter the public code of the game where your player identity exists.
              </Text>

              <FormField>
                <FormLabel htmlFor="gameCode">Game Public Code</FormLabel>
                <Input
                  id="gameCode"
                  type="text"
                  value={gamePublicCode}
                  onChange={(e) => setGamePublicCode(e.target.value.toUpperCase())}
                  placeholder="e.g., ABC123"
                  className="font-mono"
                  maxLength={10}
                  autoFocus
                />
              </FormField>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleClose}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button type="submit" className="flex-1">
                  Next
                </Button>
              </div>
            </form>
          ) : null}

          {/* Step 2: Select Player */}
          {step === 'select-player' ? (
            <>
              <Text variant="body" color="muted" className="mb-4">
                Which player identity is yours in game{' '}
                <span className="font-mono">{gamePublicCode}</span>?
              </Text>

              {isLoadingPlayers && (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
                  <Text variant="bodySmall" color="muted">
                    Loading players...
                  </Text>
                </div>
              )}

              {playersError && (
                <div className="p-3 bg-destructive/10 text-destructive rounded mb-4">
                  <Text variant="bodySmall">
                    {(playersError as any).response?.data?.error || 'Failed to load players. Please check the game code.'}
                  </Text>
                </div>
              )}

              {!isLoadingPlayers && !playersError && claimablePlayers && (
                <>
                  {claimablePlayers.length === 0 ? (
                    <div className="text-center py-8">
                      <Text variant="body" color="muted">
                        No unclaimed players found in this game. All players have been claimed.
                      </Text>
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-[400px] overflow-y-auto">
                      {claimablePlayers.map((player) => (
                        <button
                          key={player.playerId}
                          type="button"
                          onClick={() => handlePlayerSelect(player.playerId)}
                          className="w-full text-left p-3 border border-border rounded-lg hover:bg-accent hover:border-accent-foreground transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <Text variant="body" weight="medium">
                                {player.playerName}
                              </Text>
                              {player.sessionCount > 0 && (
                                <Text variant="bodySmall" color="muted">
                                  {player.sessionCount} {player.sessionCount === 1 ? 'session' : 'sessions'}
                                </Text>
                              )}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}

              <div className="flex gap-3 mt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleBack}
                  className="flex-1"
                >
                  Back
                </Button>
              </div>
            </>
          ) : null}

          {/* Step 3: Confirm */}
          {step === 'confirm' ? (
            <div className="space-y-4">
              <Text variant="body" color="muted" className="mb-4">
                Are you sure this is you?
              </Text>

              {isLoadingPreview && (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
                  <Text variant="bodySmall" color="muted">
                    Loading preview...
                  </Text>
                </div>
              )}

              {!isLoadingPreview && preview && (
                <>
                  <div className="bg-gray-800 rounded-lg p-4 space-y-3">
                    <div>
                      <Text variant="caption" color="muted">
                        Player Name
                      </Text>
                      <Text variant="body" weight="medium">
                        {preview.playerName}
                      </Text>
                    </div>
                    <div>
                      <Text variant="caption" color="muted">
                        Sessions Played
                      </Text>
                      <Text variant="body" weight="medium">
                        {preview.sessionCount}
                      </Text>
                    </div>
                  </div>

                  <div className="flex items-start gap-3 p-3 bg-info/10 border border-info/20 rounded-lg">
                    <Info className="h-5 w-5 text-info flex-shrink-0 mt-0.5" />
                    <Text variant="bodySmall" className="text-info">
                      Each player identity can only be claimed once. Make sure this is you!
                    </Text>
                  </div>
                </>
              )}

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleBack}
                  className="flex-1"
                  disabled={claimMutation.isLoading || isLoadingPreview}
                >
                  Back
                </Button>
                <Button
                  onClick={handleClaim}
                  className="flex-1"
                  disabled={claimMutation.isLoading || isLoadingPreview}
                >
                  {claimMutation.isLoading ? 'Claiming...' : 'Claim Identity'}
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
