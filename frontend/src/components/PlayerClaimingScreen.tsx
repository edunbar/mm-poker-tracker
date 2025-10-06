import { Info, UserPlus, Users } from 'lucide-react';
import { useState } from 'react';
import { AvailablePlayer } from '../types/liveGame';
import { Button } from '../shared/ui/button';
import { FormField, FormLabel } from '../shared/ui/form-field';
import { Input } from '../shared/ui/input';
import { Heading, Text } from '../shared/ui/typography';

interface PlayerClaimingScreenProps {
  availablePlayers: AvailablePlayer[];
  defaultDisplayName: string;
  onClaimExisting: (playerId: string, displayName: string) => void;
  onCreateNew: (newPlayerName: string, displayName: string) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function PlayerClaimingScreen({
  availablePlayers,
  defaultDisplayName,
  onClaimExisting,
  onCreateNew,
  onCancel,
  isLoading = false,
}: PlayerClaimingScreenProps) {
  const [mode, setMode] = useState<'select' | 'create-new'>('select');
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [newPlayerName, setNewPlayerName] = useState('');
  const [displayName, setDisplayName] = useState(defaultDisplayName);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!displayName.trim()) {
      return;
    }

    if (mode === 'create-new') {
      if (!newPlayerName.trim() || newPlayerName.trim().length < 2) {
        return;
      }
      onCreateNew(newPlayerName.trim(), displayName.trim());
    } else {
      if (!selectedPlayerId) {
        return;
      }
      onClaimExisting(selectedPlayerId, displayName.trim());
    }
  };

  const selectedPlayer = selectedPlayerId
    ? availablePlayers.find((p) => p.playerId === selectedPlayerId)
    : null;

  const isFormValid = () => {
    if (!displayName.trim() || displayName.trim().length < 2) return false;
    if (mode === 'create-new') {
      return newPlayerName.trim().length >= 2;
    }
    return !!selectedPlayerId;
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <Heading variant="h3" className="mb-2">
            Claim Your Player Identity
          </Heading>
          <Text variant="body" color="muted">
            Link your account to your poker player record
          </Text>
        </div>

        {/* Mode Selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
          <button
            type="button"
            onClick={() => {
              setMode('select');
              setSelectedPlayerId(null);
              setNewPlayerName('');
            }}
            disabled={isLoading}
            className={`
              p-4 border-2 rounded-lg transition-all
              ${mode === 'select'
                ? 'border-primary bg-primary/10'
                : 'border-border hover:border-primary/50'
              }
              ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <div className="flex items-center gap-3">
              <Users className={`h-6 w-6 ${mode === 'select' ? 'text-primary' : 'text-muted-foreground'}`} />
              <div className="text-left">
                <Text variant="body" weight="medium">
                  I'm an existing player
                </Text>
                <Text variant="bodySmall" color="muted">
                  Select from {availablePlayers.length} available {availablePlayers.length === 1 ? 'player' : 'players'}
                </Text>
              </div>
            </div>
          </button>

          <button
            type="button"
            onClick={() => {
              setMode('create-new');
              setSelectedPlayerId(null);
              setNewPlayerName('');
            }}
            disabled={isLoading}
            className={`
              p-4 border-2 rounded-lg transition-all
              ${mode === 'create-new'
                ? 'border-primary bg-primary/10'
                : 'border-border hover:border-primary/50'
              }
              ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <div className="flex items-center gap-3">
              <UserPlus className={`h-6 w-6 ${mode === 'create-new' ? 'text-primary' : 'text-muted-foreground'}`} />
              <div className="text-left">
                <Text variant="body" weight="medium">
                  I'm a new player
                </Text>
                <Text variant="bodySmall" color="muted">
                  Create a new player record
                </Text>
              </div>
            </div>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-card border border-border rounded-lg p-6 space-y-6">
          {/* Existing Player Selection */}
          {mode === 'select' && (
            <div>
              <FormLabel className="mb-3">Select Your Player</FormLabel>
              {availablePlayers.length === 0 ? (
                <div className="text-center py-8 bg-muted/30 rounded-lg">
                  <Text variant="body" color="muted">
                    No unclaimed players available. Try creating a new player instead.
                  </Text>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto">
                  {availablePlayers.map((player) => (
                    <button
                      key={player.playerId}
                      type="button"
                      onClick={() => setSelectedPlayerId(player.playerId)}
                      disabled={isLoading}
                      className={`
                        text-left p-3 border-2 rounded-lg transition-all
                        ${selectedPlayerId === player.playerId
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:border-primary/50'
                        }
                        ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                      `}
                    >
                      <Text variant="body" weight="medium">
                        {player.playerName}
                      </Text>
                      {player.sessionCount > 0 && (
                        <Text variant="bodySmall" color="muted">
                          {player.sessionCount} {player.sessionCount === 1 ? 'session' : 'sessions'}
                        </Text>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* New Player Creation */}
          {mode === 'create-new' && (
            <FormField>
              <FormLabel htmlFor="newPlayerName">Player Name</FormLabel>
              <Input
                id="newPlayerName"
                type="text"
                value={newPlayerName}
                onChange={(e) => setNewPlayerName(e.target.value)}
                placeholder="Enter your player name"
                minLength={2}
                maxLength={50}
                disabled={isLoading}
                autoFocus
              />
              <Text variant="caption" color="muted" className="mt-1">
                This will be your permanent player identity for this game
              </Text>
            </FormField>
          )}

          {/* Display Name for Live Game */}
          <FormField>
            <FormLabel htmlFor="displayName">Display Name for This Session</FormLabel>
            <Input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="How you'll appear in this live game"
              minLength={2}
              maxLength={50}
              disabled={isLoading}
            />
            <Text variant="caption" color="muted" className="mt-1">
              This is just for this live game session
            </Text>
          </FormField>

          {/* Info Banner */}
          {selectedPlayer && (
            <div className="flex items-start gap-3 p-3 bg-info/10 border border-info/20 rounded-lg">
              <Info className="h-5 w-5 text-info flex-shrink-0 mt-0.5" />
              <Text variant="bodySmall" className="text-info">
                You'll be linked to <strong>{selectedPlayer.playerName}</strong> with {selectedPlayer.sessionCount} previous {selectedPlayer.sessionCount === 1 ? 'session' : 'sessions'}
              </Text>
            </div>
          )}

          {mode === 'create-new' && newPlayerName.trim() && (
            <div className="flex items-start gap-3 p-3 bg-info/10 border border-info/20 rounded-lg">
              <Info className="h-5 w-5 text-info flex-shrink-0 mt-0.5" />
              <Text variant="bodySmall" className="text-info">
                A new player record will be created for <strong>{newPlayerName}</strong>
              </Text>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              className="flex-1"
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={!isFormValid() || isLoading}
            >
              {isLoading ? 'Joining...' : 'Claim & Join Game'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
