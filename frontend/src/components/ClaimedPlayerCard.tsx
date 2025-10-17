import { X } from 'lucide-react';
import { useState } from 'react';
import { useUnclaimPlayer, type PlayerIdentityClaim } from '../api/playerIdentityClaim';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../shared/ui/button';
import { Heading, Text } from '../shared/ui/typography';

interface ClaimedPlayerCardProps {
  claim: PlayerIdentityClaim;
}

export function ClaimedPlayerCard({ claim }: ClaimedPlayerCardProps) {
  const unclaimMutation = useUnclaimPlayer();
  const { showSuccess, showError } = useToast();
  const [showUnclaimConfirm, setShowUnclaimConfirm] = useState(false);

  const handleUnclaim = async () => {
    try {
      await unclaimMutation.mutateAsync(claim.claimId);
      showSuccess('Success', 'Player identity unclaimed successfully');
      setShowUnclaimConfirm(false);
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to unclaim player identity';
      showError('Error', errorMessage);
    }
  };

  const handleCloseConfirm = () => {
    setShowUnclaimConfirm(false);
  };

  // Format the claimed date
  const claimedDate = new Date(claim.claimedAt).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <>
      <div className="border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-colors">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <Heading variant="h5" className="mb-1 truncate">
              {claim.playerName}
            </Heading>

            {/* Display games */}
            {claim.games && claim.games.length > 0 && (
              <div className="space-y-1 mb-2">
                {claim.games.map((game) => (
                  <Text key={game.gameId} variant="bodySmall" color="muted">
                    {game.gameTitle || 'Untitled Game'} •{' '}
                    <span className="font-mono">{game.publicCode}</span>
                  </Text>
                ))}
              </div>
            )}

            <Text variant="caption" color="muted">
              Claimed {claimedDate}
            </Text>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowUnclaimConfirm(true)}
            className="ml-4 flex-shrink-0"
          >
            Unclaim
          </Button>
        </div>
      </div>

      {/* Unclaim Confirmation Modal */}
      {showUnclaimConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-md w-full">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <Heading variant="h4">Unclaim Player Identity?</Heading>
              <Button
                onClick={handleCloseConfirm}
                variant="ghost"
                size="icon-sm"
                disabled={unclaimMutation.isLoading}
              >
                <X className="h-6 w-6" />
              </Button>
            </div>

            {/* Body */}
            <div className="p-6 space-y-6">
              <Text variant="body" color="muted">
                Are you sure you want to unclaim "<strong className="font-semibold text-foreground">{claim.playerName}</strong>"? This identity will become available for claiming again.
              </Text>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCloseConfirm}
                  className="flex-1"
                  disabled={unclaimMutation.isLoading}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleUnclaim}
                  className="flex-1"
                  disabled={unclaimMutation.isLoading}
                >
                  {unclaimMutation.isLoading ? 'Unclaiming...' : 'Yes, Unclaim'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
