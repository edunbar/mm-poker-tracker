import { X } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useRequestBuyIn, useParticipants } from '../api/liveGame';
import { useClerkAuth } from '../hooks/useClerkAuth';
import { Button } from '../shared/ui/button';
import { FormField, FormLabel } from '../shared/ui/form-field';
import { Input } from '../shared/ui/input';
import { Heading, Text } from '../shared/ui/typography';

interface BuyInModalProps {
  joinCode: string;
  minBuyIn: number;
  maxBuyIn: number | null;
  onClose: () => void;
}

export function BuyInModal({ joinCode, minBuyIn, maxBuyIn, onClose }: BuyInModalProps) {
  const { user } = useClerkAuth();
  const [amount, setAmount] = useState(minBuyIn.toString());
  const [status, setStatus] = useState<'idle' | 'pending'>('idle');
  const buyInMutation = useRequestBuyIn();

  // Track initial totalBuyIns when entering pending state
  const initialBuyInsRef = useRef<number | null>(null);

  // Watch participant stats for approval (SSE will update this)
  const { data: participants = [] } = useParticipants(joinCode);
  const myParticipant = participants.find(p => p.userId === user?.id);

  // Auto-close when buy-in is approved (totalBuyIns increases)
  useEffect(() => {
    if (status === 'pending' && myParticipant) {
      // Store initial value on first render in pending state
      if (initialBuyInsRef.current === null) {
        initialBuyInsRef.current = myParticipant.stats.totalBuyIns;
      } else if (myParticipant.stats.totalBuyIns > initialBuyInsRef.current) {
        // Buy-in was approved! Close modal
        onClose();
      }
    }
  }, [status, myParticipant, onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount < minBuyIn || (maxBuyIn && numAmount > maxBuyIn)) {
      return;
    }

    try {
      setStatus('pending');
      await buyInMutation.mutateAsync({
        joinCode,
        amount: numAmount
      });
      // Transaction created successfully
    } catch (error) {
      setStatus('idle');
    }
  };

  const quickAmounts = [50, 100, 200, 500].filter(amt =>
    amt >= minBuyIn && (!maxBuyIn || amt <= maxBuyIn)
  );

  if (status === 'pending') {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-background rounded-lg shadow-xl max-w-md w-full">
          <div className="flex items-center justify-between p-6 border-b border-border">
            <Heading variant="h4">⏳ Buy-In Pending</Heading>
            <Button onClick={onClose} variant="ghost" size="icon-sm">
              <X className="h-6 w-6" />
            </Button>
          </div>

          <div className="p-6 space-y-4">
            <div className="bg-warning/20 border border-warning/50 rounded-lg p-4">
              <Text variant="bodySmall" className="text-warning">
                Amount: ${amount}
              </Text>
              <Text variant="bodySmall" className="text-warning mt-2">
                Waiting for admin approval...
              </Text>
            </div>

            <Text variant="caption" color="muted">
              Your buy-in request has been sent. Once approved, you'll receive chips from the admin.
            </Text>

            <Button variant="outline" onClick={onClose} className="w-full">
              Done
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-md w-full">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <Heading variant="h4">Buy In</Heading>
          <Button onClick={onClose} variant="ghost" size="icon-sm">
            <X className="h-6 w-6" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <>
            <FormField>
              <FormLabel htmlFor="amount">Amount</FormLabel>
              <Input
                id="amount"
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                min={minBuyIn}
                max={maxBuyIn || undefined}
                step="0.01"
                required
                autoFocus
              />
              <Text variant="caption" color="muted" className="mt-1">
                Min: ${minBuyIn}
                {maxBuyIn && ` | Max: $${maxBuyIn}`}
              </Text>
            </FormField>

            {quickAmounts.length > 0 && (
            <div>
              <Text variant="caption" color="muted" className="mb-2">
                Quick amounts:
              </Text>
              <div className="grid grid-cols-4 gap-2">
                {quickAmounts.map(amt => (
                  <Button
                    key={amt}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setAmount(amt.toString())}
                  >
                    ${amt}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <div className="bg-muted rounded-lg p-4">
            <Text variant="bodySmall" color="muted">
              Note: Admin must approve before you receive chips.
            </Text>
          </div>

          {buyInMutation.error && (
            <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-4">
              <Text variant="bodySmall" className="text-destructive">
                {(buyInMutation.error as any)?.response?.data?.error ||
                 'Failed to request buy-in'}
              </Text>
            </div>
          )}

          <div className="flex gap-3">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button type="submit" disabled={buyInMutation.isLoading} className="flex-1">
              {buyInMutation.isLoading ? 'Requesting...' : 'Request Buy-In'}
            </Button>
          </div>
          </>
        </form>
      </div>
    </div>
  );
}
