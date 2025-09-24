import { CheckCircle, Users, X } from 'lucide-react';
import { useState } from 'react';
import { Button } from '../../../shared/ui/button';
import { Heading, Text } from '../../../shared/ui/typography';

interface UnmatchedPlayer {
  display_name: string;
  external_id: string | null;
}

interface PlayerMappingModalProps {
  unmatchedPlayers: UnmatchedPlayer[];
  existingPlayers: Array<{
    id: string;
    display_name: string;
    external_id?: string;
  }>;
  onConfirm: (mappings: Record<string, string>) => void;
  onCancel: () => void;
}

export default function PlayerMappingModal({
  unmatchedPlayers,
  existingPlayers,
  onConfirm,
  onCancel
}: PlayerMappingModalProps) {
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [newPlayers, setNewPlayers] = useState<Set<string>>(new Set());

  const getPlayerKey = (player: UnmatchedPlayer) => {
    return JSON.stringify([player.display_name, player.external_id]);
  };

  const handleMapping = (playerKey: string, playerId: string) => {
    setMappings(prev => ({ ...prev, [playerKey]: playerId }));
    if (newPlayers.has(playerKey)) {
      const updated = new Set(newPlayers);
      updated.delete(playerKey);
      setNewPlayers(updated);
    }
  };

  const handleCreateNew = (playerKey: string) => {
    setNewPlayers(prev => new Set(prev).add(playerKey));
    if (mappings[playerKey]) {
      const updated = { ...mappings };
      delete updated[playerKey];
      setMappings(updated);
    }
  };

  const canConfirm = unmatchedPlayers.every(player => {
    const key = getPlayerKey(player);
    return mappings[key] || newPlayers.has(key);
  });

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <Heading variant="h3">Map Players</Heading>
              <Text variant="caption" color="muted" className="mt-1">
                {unmatchedPlayers.length} player{unmatchedPlayers.length !== 1 ? 's' : ''} need to be matched
              </Text>
            </div>
          </div>
          <Button
            onClick={onCancel}
            variant="ghost"
            size="icon-sm"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <div className="space-y-4">
            {unmatchedPlayers.map((player) => {
              const key = getPlayerKey(player);
              const isNewPlayer = newPlayers.has(key);
              const selectedPlayerId = mappings[key];

              return (
                <div
                  key={key}
                  className="bg-muted/50 rounded-lg p-4 border border-border"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <Text variant="body" weight="semibold">
                        {player.display_name}
                      </Text>
                      {player.external_id && (
                        <Text variant="caption" color="muted">
                          ID: {player.external_id}
                        </Text>
                      )}
                    </div>
                    {(selectedPlayerId || isNewPlayer) && (
                      <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                    )}
                  </div>

                  <div className="space-y-2">
                    <label className="block">
                      <Text variant="caption" weight="medium" className="mb-1 block">
                        Match to existing player:
                      </Text>
                      <select
                        value={selectedPlayerId || ''}
                        onChange={(e) => handleMapping(key, e.target.value)}
                        className="w-full px-3 py-2 border border-input bg-background text-foreground text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                        disabled={isNewPlayer}
                      >
                        <option value="">-- Select player --</option>
                        {existingPlayers.map((existingPlayer) => (
                          <option key={existingPlayer.id} value={existingPlayer.id}>
                            {existingPlayer.display_name}
                            {existingPlayer.external_id ? ` (${existingPlayer.external_id})` : ''}
                          </option>
                        ))}
                      </select>
                    </label>

                    <div className="flex items-center gap-2">
                      <div className="flex-1 border-t border-border" />
                      <Text variant="caption" color="muted">or</Text>
                      <div className="flex-1 border-t border-border" />
                    </div>

                    <Button
                      onClick={() => handleCreateNew(key)}
                      variant={isNewPlayer ? 'default' : 'outline'}
                      size="sm"
                      className="w-full"
                    >
                      {isNewPlayer ? '✓ Creating New Player' : 'Create New Player'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>

          {unmatchedPlayers.length > 0 && (
            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
              <Text variant="caption" className="text-blue-900 dark:text-blue-100">
                <strong>Note:</strong> You must either match each player to an existing player or create a new player record.
              </Text>
            </div>
          )}
        </div>

        <div className="flex gap-3 p-6 border-t border-border">
          <Button
            onClick={onCancel}
            variant="outline"
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            onClick={() => onConfirm(mappings)}
            disabled={!canConfirm}
            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Confirm Mappings
          </Button>
        </div>
      </div>
    </div>
  );
}