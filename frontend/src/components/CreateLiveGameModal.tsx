import { X, AlertCircle } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useCreateLiveGame } from '../api/liveGame';
import { Button } from '../shared/ui/button';
import { FormField, FormLabel } from '../shared/ui/form-field';
import { Input } from '../shared/ui/input';
import { Heading, Text } from '../shared/ui/typography';

interface CreateLiveGameModalProps {
  gameId: string;
  onClose: () => void;
  onSuccess: (joinCode: string, liveGameId: string) => void;
}

export function CreateLiveGameModal({ gameId, onClose, onSuccess }: CreateLiveGameModalProps) {
  const navigate = useNavigate();
  const { publicCode } = useParams<{ publicCode: string }>();
  const [smallBlind, setSmallBlind] = useState('1');
  const [bigBlind, setBigBlind] = useState('2');
  const [minBuyIn, setMinBuyIn] = useState('20');
  const [maxBuyIn, setMaxBuyIn] = useState('');
  const [existingJoinCode, setExistingJoinCode] = useState<string | null>(null);

  const createMutation = useCreateLiveGame();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const data: any = {
        minBuyIn: parseFloat(minBuyIn),
      };

      if (smallBlind) {
        data.smallBlind = parseFloat(smallBlind);
      }
      if (bigBlind) {
        data.bigBlind = parseFloat(bigBlind);
      }
      if (maxBuyIn) {
        data.maxBuyIn = parseFloat(maxBuyIn);
      }

      const result = await createMutation.mutateAsync({
        gameId,
        data
      });

      onSuccess(result.joinCode, result.liveGameId);
    } catch (error: any) {
      // Check for 409 conflict (active game already exists)
      if (error?.response?.status === 409 && error?.response?.data?.existing_join_code) {
        setExistingJoinCode(error.response.data.existing_join_code);
      }
    }
  };

  const handleGoToExistingGame = () => {
    if (existingJoinCode && publicCode) {
      navigate(`/live/${publicCode}/${existingJoinCode}/admin`);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-md w-full">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <Heading variant="h4">Start Live Game</Heading>
          <Button onClick={onClose} variant="ghost" size="icon-sm">
            <X className="h-6 w-6" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <>
            <div className="grid grid-cols-2 gap-4">
            <FormField>
              <FormLabel htmlFor="smallBlind">Small Blind (optional)</FormLabel>
              <Input
                id="smallBlind"
                type="number"
                value={smallBlind}
                onChange={(e) => setSmallBlind(e.target.value)}
                step="0.01"
                min="0"
                placeholder="1"
              />
            </FormField>

            <FormField>
              <FormLabel htmlFor="bigBlind">Big Blind (optional)</FormLabel>
              <Input
                id="bigBlind"
                type="number"
                value={bigBlind}
                onChange={(e) => setBigBlind(e.target.value)}
                step="0.01"
                min="0"
                placeholder="2"
              />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField>
              <FormLabel htmlFor="minBuyIn">Minimum Buy-In</FormLabel>
              <Input
                id="minBuyIn"
                type="number"
                value={minBuyIn}
                onChange={(e) => setMinBuyIn(e.target.value)}
                step="0.01"
                min="0.01"
                required
              />
            </FormField>

            <FormField>
              <FormLabel htmlFor="maxBuyIn">Max Buy-In (optional)</FormLabel>
              <Input
                id="maxBuyIn"
                type="number"
                value={maxBuyIn}
                onChange={(e) => setMaxBuyIn(e.target.value)}
                step="0.01"
                min="0"
                placeholder="No limit"
              />
            </FormField>
          </div>

          {existingJoinCode ? (
            <div className="bg-warning/10 border border-warning/50 rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-warning mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <Text variant="bodySmall" weight="semibold" className="text-warning">
                    Live Game Already Running
                  </Text>
                  <Text variant="bodySmall" color="muted" className="mt-1">
                    Only one live game can run at a time. A game is already active with code:{' '}
                    <span className="font-mono font-semibold text-foreground">{existingJoinCode}</span>
                  </Text>
                </div>
              </div>
              <Button
                type="button"
                onClick={handleGoToExistingGame}
                className="w-full"
                variant="default"
              >
                Go to Existing Game
              </Button>
            </div>
          ) : createMutation.error && (
            <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-4">
              <Text variant="bodySmall" className="text-destructive">
                {(createMutation.error as any)?.response?.data?.error ||
                 'Failed to create live game'}
              </Text>
            </div>
          )}

          <div className="flex gap-3">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isLoading || !!existingJoinCode}
              className="flex-1"
            >
              {createMutation.isLoading ? 'Creating...' : 'Start Game'}
            </Button>
          </div>
          </>
        </form>
      </div>
    </div>
  );
}
