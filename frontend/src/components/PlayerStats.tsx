import type { Participant } from '../types/liveGame';
import { Heading, Text } from '../shared/ui/typography';

interface PlayerStatsProps {
  participant: Participant;
}

export function PlayerStats({ participant }: PlayerStatsProps) {
  const { stats } = participant;
  const netColorClass = stats.netResult >= 0 ? 'text-success' : 'text-destructive';

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <Heading variant="h4" className="mb-4">Your Stats</Heading>

      <div className="space-y-4">
        <div>
          <Text variant="caption" color="muted">Buy-ins</Text>
          <Heading variant="h4" className="mt-1">${stats.totalBuyIns.toFixed(2)}</Heading>
        </div>

        <div className="pt-4 border-t border-border">
          <Text variant="caption" color="muted">Net Result</Text>
          <Heading variant="h3" className={`mt-1 ${netColorClass}`}>
            {stats.netResult >= 0 ? '+' : ''}${stats.netResult.toFixed(2)}
          </Heading>
        </div>
      </div>
    </div>
  );
}
