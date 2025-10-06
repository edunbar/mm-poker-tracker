import { Check, X } from 'lucide-react';
import { useApproveTransaction, useRejectTransaction } from '../api/liveGame';
import type { LiveGameTransaction, Participant } from '../types/liveGame';
import { Button } from '../shared/ui/button';
import { Text } from '../shared/ui/typography';

interface PendingTransactionsListProps {
  joinCode: string;
  transactions: LiveGameTransaction[];
  participants: Participant[];
}

export function PendingTransactionsList({ joinCode, transactions, participants }: PendingTransactionsListProps) {
  const approveMutation = useApproveTransaction();
  const rejectMutation = useRejectTransaction();

  // Helper function to get participant display name
  const getParticipantDisplayName = (participantId: string): string => {
    const participant = participants.find(p => p.participantId === participantId);
    return participant?.displayName || 'Unknown';
  };

  const handleApprove = async (transaction: LiveGameTransaction) => {
    try {
      await approveMutation.mutateAsync({
        joinCode,
        transactionId: transaction.transactionId,
      });
    } catch (error) {
      // Error handled by mutation
      console.error('Failed to approve transaction:', error);
    }
  };

  const handleReject = async (transactionId: string) => {
    try {
      await rejectMutation.mutateAsync({
        joinCode,
        transactionId,
        reason: 'Rejected by admin',
      });
    } catch (error) {
      // Error handled by mutation
      console.error('Failed to reject transaction:', error);
    }
  };

  const isProcessing = () => {
    return approveMutation.isLoading || rejectMutation.isLoading;
  };

  if (transactions.length === 0) {
    return (
      <div className="text-center py-8">
        <Text variant="body" color="muted">
          No pending transactions
        </Text>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {transactions.map((transaction) => {
        const isBuyIn = transaction.transactionType === 'buy_in';
        const isCashOut = transaction.transactionType === 'cash_out';

        return (
          <div
            key={transaction.transactionId}
            className="flex items-center justify-between bg-background rounded-lg border border-border p-4"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Text variant="body" weight="medium">
                  {getParticipantDisplayName(transaction.participantId)}
                </Text>
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                  isBuyIn
                    ? 'bg-success/20 text-success'
                    : 'bg-warning/20 text-warning'
                }`}>
                  {isBuyIn && '💵 Buy-In'}
                  {isCashOut && '🚪 Cash-Out'}
                </span>
              </div>

              <div className="flex gap-4">
                <div>
                  <Text variant="caption" color="muted">Amount</Text>
                  <Text variant="body" weight="medium" className="mt-0.5">
                    ${transaction.amount.toFixed(2)}
                  </Text>
                </div>

                {transaction.originalAmount && (
                  <div>
                    <Text variant="caption" color="muted">Original Amount</Text>
                    <Text variant="body" weight="medium" className="mt-0.5">
                      ${transaction.originalAmount.toFixed(2)}
                    </Text>
                  </div>
                )}
              </div>

              <Text variant="caption" color="muted" className="mt-1">
                Requested {new Date(transaction.createdAt).toLocaleTimeString()}
              </Text>
            </div>

            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleReject(transaction.transactionId)}
                disabled={isProcessing()}
                className="text-destructive border-destructive/50 hover:bg-destructive/10"
              >
                <X className="h-4 w-4 mr-1" />
                Reject
              </Button>
              <Button
                size="sm"
                onClick={() => handleApprove(transaction)}
                disabled={isProcessing()}
                className="bg-success hover:bg-success/90"
              >
                <Check className="h-4 w-4 mr-1" />
                Approve
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
