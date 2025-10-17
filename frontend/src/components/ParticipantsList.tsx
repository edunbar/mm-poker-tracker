import type { Participant } from '../types/liveGame';
import { Text } from '../shared/ui/typography';

interface ParticipantsListProps {
  participants: Participant[];
  currentUserId?: string;
}

export function ParticipantsList({ participants, currentUserId }: ParticipantsListProps) {
  return (
    <div className="space-y-3">
      {participants.map(participant => {
        const isCurrentUser = participant.userId === currentUserId;
        const hasChips = participant.stats.chipsOnTable > 0;
        const hasCashedOut = participant.stats.totalCashOuts > 0;
        const isPlaying = hasChips && !hasCashedOut;

        return (
          <div
            key={participant.participantId}
            className={`flex items-center justify-between p-3 rounded-lg ${
              isCurrentUser
                ? 'bg-primary/10 border border-primary/30'
                : 'bg-muted'
            }`}
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Text variant="body" weight="medium">
                  {participant.displayName}
                  {isCurrentUser && ' (You)'}
                </Text>
                {hasCashedOut ? (
                  <span className="px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground">
                    Cashed Out
                  </span>
                ) : isPlaying ? (
                  <span className="text-success text-xs">● Playing</span>
                ) : (
                  <span className="text-muted-foreground text-xs">● Waiting</span>
                )}
              </div>
              <Text variant="caption" color="muted">
                In: ${participant.stats.totalBuyIns.toFixed(2)}
                {hasCashedOut && ` | Out: $${participant.stats.totalCashOuts.toFixed(2)}`}
                {hasCashedOut && (
                  <span className={participant.stats.netResult >= 0 ? 'text-success' : 'text-destructive'}>
                    {' '}({participant.stats.netResult >= 0 ? '+' : ''}${participant.stats.netResult.toFixed(2)})
                  </span>
                )}
              </Text>
            </div>

            {isPlaying && (
              <div className="text-right">
                <Text variant="bodySmall" weight="medium">
                  ${participant.stats.chipsOnTable.toFixed(2)}
                </Text>
                <Text variant="caption" color="muted">on table</Text>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
