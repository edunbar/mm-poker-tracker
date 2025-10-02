import { PlayerSummaryRow } from "../../../entities/game/types";
import { Heading, Text } from "../../../shared/ui/typography";
import { usePlayerSummaries } from "../api/getPlayerSummaries";
import GameDataTable from "../components/GameDataTable";

interface GameSummaryPageProps {
  publicCode: string;
}

export default function GameSummaryPage({ publicCode }: GameSummaryPageProps) {
  const { data, isLoading, error } = usePlayerSummaries(publicCode);
  const rows: PlayerSummaryRow[] = data?.rows || [];


  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4 md:px-6 lg:px-8">
        <div className="mb-8">
          <Heading variant="h1">Game Summary</Heading>
          <Text variant="body" color="muted" className="mt-2">
            Player statistics and performance metrics
          </Text>
        </div>

        {isLoading && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            Loading...
          </div>
        )}

        {!!error && (
          <div className="mb-6 p-4 bg-destructive/10 border-l-4 border-destructive rounded">
            <Text variant="body" color="destructive" weight="medium">Error</Text>
            <Text variant="body" color="destructive">
              {String(error instanceof Error ? error.message : "An error occurred while loading the game data")}
            </Text>
          </div>
        )}

        {!isLoading && !error && rows.length > 0 && (
          <GameDataTable
            playersInfos={rows}
            setEditableData={() => {}}
          />
        )}

        {!isLoading && !error && rows.length === 0 && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            <Text variant="body" color="muted">No player data available for this game.</Text>
          </div>
        )}
      </div>
    </div>
  );
}
