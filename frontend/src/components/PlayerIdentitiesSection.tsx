import { useState } from 'react';
import { useMyPlayerClaims } from '../api/playerIdentityClaim';
import { Button } from '../shared/ui/button';
import { Text } from '../shared/ui/typography';
import { ClaimedPlayerCard } from './ClaimedPlayerCard';
import { ClaimPlayerModal } from './ClaimPlayerModal';

export function PlayerIdentitiesSection() {
  const { data: claims, isLoading, refetch } = useMyPlayerClaims();
  const [showClaimModal, setShowClaimModal] = useState(false);

  const handleClaimSuccess = () => {
    setShowClaimModal(false);
    refetch(); // Refresh the claims list
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
        <Text variant="bodySmall" color="muted">
          Loading player identities...
        </Text>
      </div>
    );
  }

  if (!claims || claims.length === 0) {
    return (
      <>
        <div className="text-center py-8">
          <Text variant="body" color="muted" className="mb-4">
            You haven't claimed any player identities yet
          </Text>
          <Button onClick={() => setShowClaimModal(true)}>
            Claim Your First Identity
          </Button>
        </div>

        {showClaimModal && (
          <ClaimPlayerModal
            onClose={() => setShowClaimModal(false)}
            onSuccess={handleClaimSuccess}
          />
        )}
      </>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {claims.map((claim) => (
          <ClaimedPlayerCard key={claim.claimId} claim={claim} />
        ))}

        <Button
          variant="outline"
          onClick={() => setShowClaimModal(true)}
          className="w-full"
        >
          + Claim Another Identity
        </Button>
      </div>

      {showClaimModal && (
        <ClaimPlayerModal
          onClose={() => setShowClaimModal(false)}
          onSuccess={handleClaimSuccess}
        />
      )}
    </>
  );
}
