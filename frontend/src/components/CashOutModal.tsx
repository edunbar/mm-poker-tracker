import { X } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useRequestCashOut, useParticipants } from '../api/liveGame';
import { useClerkAuth } from '../hooks/useClerkAuth';
import { Button } from '../shared/ui/button';
import { FormField, FormLabel } from '../shared/ui/form-field';
import { Input } from '../shared/ui/input';
import { Heading, Text } from '../shared/ui/typography';

interface CashOutModalProps {
  joinCode: string;
  chipsOnTable: number;
  totalBuyIns: number;
  onClose: () => void;
}

export function CashOutModal({
  joinCode,
  chipsOnTable,
  totalBuyIns,
  onClose
}: CashOutModalProps) {
  const { user } = useClerkAuth();
  const [amount, setAmount] = useState(''); // Don't pre-fill - player counts their actual chips
  const [status, setStatus] = useState<'idle' | 'pending'>('idle');
  const cashOutMutation = useRequestCashOut();

  // Track initial totalCashOuts when entering pending state
  const initialCashOutsRef = useRef<number | null>(null);

  // Watch participant stats for approval (SSE will update this)
  const { data: participants = [] } = useParticipants(joinCode);
  const myParticipant = participants.find(p => p.userId === user?.id);

  // Auto-close when cash-out is approved (totalCashOuts increases)
  useEffect(() => {
    if (status === 'pending' && myParticipant) {
      // Store initial value on first render in pending state
      if (initialCashOutsRef.current === null) {
        initialCashOutsRef.current = myParticipant.stats.totalCashOuts;
      } else if (myParticipant.stats.totalCashOuts > initialCashOutsRef.current) {
        // Cash-out was approved! Close modal
        onClose();
      }
    }
  }, [status, myParticipant, onClose]);

  const netResult = amount ? parseFloat(amount) - totalBuyIns : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount < 0) {
      return;
    }

    try {
      setStatus('pending');
      await cashOutMutation.mutateAsync({
        joinCode,
        amount: numAmount
      });
      // Success
    } catch (error) {
      setStatus('idle');
    }
  };

  if (status === 'pending') {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-background rounded-lg shadow-xl max-w-md w-full">
          <div className="flex items-center justify-between p-6 border-b border-border">
            <Heading variant="h4">⏳ Cash-Out Pending</Heading>
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
                Please bring your chips to the admin for verification.
              </Text>
            </div>

            <Text variant="caption" color="muted">
              Waiting for admin approval...
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
          <Heading variant="h4">Cash Out</Heading>
          <Button onClick={onClose} variant="ghost" size="icon-sm">
            <X className="h-6 w-6" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <>
            <div className="bg-muted rounded-lg p-4 space-y-2">
            <div className="flex justify-between">
              <Text variant="bodySmall" color="muted">Total Buy-ins:</Text>
              <Text variant="bodySmall" weight="medium">${totalBuyIns.toFixed(2)}</Text>
            </div>
          </div>

          <div className="bg-primary/10 border border-primary/30 rounded-lg p-4">
            <Text variant="bodySmall" className="text-primary">
              💡 Count your chips at the table and enter the TOTAL amount you're leaving with tonight.
            </Text>
          </div>

          <FormField>
            <FormLabel htmlFor="amount">Total Chips (Final Count)</FormLabel>
            <Input
              id="amount"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              min="0"
              step="0.01"
              required
              autoFocus
              placeholder="Count your chips..."
            />
            <Text variant="caption" color="muted" className="mt-1">
              This is what you're taking home tonight (expected: ${chipsOnTable.toFixed(2)} based on buy-ins)
            </Text>
          </FormField>

          {amount && (
            <div className={`rounded-lg p-4 ${
              netResult >= 0
                ? 'bg-success/20 border border-success/50'
                : 'bg-destructive/20 border border-destructive/50'
            }`}>
              <Text variant="bodySmall" color="muted" className="mb-1">
                Your Net Result Tonight:
              </Text>
              <Heading variant="h3" className={netResult >= 0 ? 'text-success' : 'text-destructive'}>
                {netResult >= 0 ? '+' : ''}${netResult.toFixed(2)}
                {netResult >= 0 ? ' 🎉' : ' 📉'}
              </Heading>
              <Text variant="caption" color="muted" className="mt-1">
                You bought in for ${totalBuyIns.toFixed(2)}
              </Text>
            </div>
          )}

          <div className="bg-warning/10 border border-warning/30 rounded-lg p-4">
            <Text variant="bodySmall" className="text-warning">
              ⚠️ Admin will verify your chip count. Make sure it's accurate!
            </Text>
          </div>

          {cashOutMutation.error && (
            <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-4">
              <Text variant="bodySmall" className="text-destructive">
                {(cashOutMutation.error as any)?.response?.data?.error ||
                 'Failed to request cash-out'}
              </Text>
            </div>
          )}

          <div className="flex gap-3">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button type="submit" disabled={cashOutMutation.isLoading} className="flex-1">
              {cashOutMutation.isLoading ? 'Requesting...' : 'Request Cash-Out'}
            </Button>
          </div>
          </>
        </form>
      </div>
    </div>
  );
}
