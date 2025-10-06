import type { Participant } from '../types/liveGame';
import { Text } from '../shared/ui/typography';

interface AdminParticipantsListProps {
  participants: Participant[];
}

// TODO: Chip adjustment feature not yet implemented in backend
// When implementing, add endpoints for manual chip adjustments and hook here
export function AdminParticipantsList({ participants }: AdminParticipantsListProps) {

  if (participants.length === 0) {
    return (
      <div className="text-center py-8">
        <Text variant="body" color="muted">
          No players have joined yet
        </Text>
      </div>
    );
  }

  // Sort by chips on table (descending), then by net result
  const sortedParticipants = [...participants].sort((a, b) => {
    // Players still playing (with chips) first
    if (a.stats.chipsOnTable > 0 && b.stats.chipsOnTable === 0) return -1;
    if (a.stats.chipsOnTable === 0 && b.stats.chipsOnTable > 0) return 1;
    // Then sort by chips on table (or net result if both cashed out)
    return b.stats.chipsOnTable - a.stats.chipsOnTable;
  });

  return (
    <div className="space-y-3">
      {sortedParticipants.map((participant) => {
        const hasChips = participant.stats.chipsOnTable > 0;
        const hasCashedOut = participant.stats.totalCashOuts > 0;
        // Net result is already calculated by backend: total_cash_outs - total_buy_ins
        const netResult = participant.stats.netResult;

        return (
          <div
            key={participant.participantId}
            className={`rounded-lg border p-4 ${
              hasChips
                ? 'bg-background border-border'
                : 'bg-muted border-muted'
            }`}
          >
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-1">
                <Text variant="body" weight="medium">
                  {participant.displayName}
                </Text>
                {hasCashedOut && (
                  <span className="px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground">
                    Cashed Out
                  </span>
                )}
              </div>
              {participant.userId && (
                <Text variant="caption" color="muted">
                  User ID: {participant.userId.slice(0, 8)}...
                </Text>
              )}
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <Text variant="caption" color="muted">Chips on Table</Text>
                <Text variant="body" weight="medium" className="mt-0.5">
                  ${participant.stats.chipsOnTable.toFixed(2)}
                </Text>
              </div>
              <div>
                <Text variant="caption" color="muted">Total Buy-ins</Text>
                <Text variant="body" weight="medium" className="mt-0.5">
                  ${participant.stats.totalBuyIns.toFixed(2)}
                </Text>
              </div>
              <div>
                <Text variant="caption" color="muted">Total Cash-outs</Text>
                <Text variant="body" weight="medium" className="mt-0.5">
                  ${participant.stats.totalCashOuts.toFixed(2)}
                </Text>
              </div>
              <div>
                <Text variant="caption" color="muted">Net Result</Text>
                <Text
                  variant="body"
                  weight="medium"
                  className={`mt-0.5 ${
                    netResult >= 0 ? 'text-success' : 'text-destructive'
                  }`}
                >
                  {netResult >= 0 ? '+' : ''}${netResult.toFixed(2)}
                </Text>
              </div>
            </div>

            {participant.joinedAt && (
              <Text variant="caption" color="muted" className="mt-3">
                Joined {new Date(participant.joinedAt).toLocaleString()}
              </Text>
            )}
          </div>
        );
      })}
    </div>
  );
}
