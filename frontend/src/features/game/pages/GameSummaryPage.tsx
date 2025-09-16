import { PlayerSummaryRow } from "../../../entities/game/types";
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
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Game Summary</h1>
          <p className="mt-2 text-muted-foreground">
            Player statistics and performance metrics
          </p>
        </div>

        {isLoading && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            Loading...
          </div>
        )}

        {!!error && (
          <div className="mb-6 p-4 bg-destructive/10 border-l-4 border-destructive rounded">
            <div className="text-destructive font-medium">Error</div>
            <div className="text-destructive">
              {String(error instanceof Error ? error.message : "An error occurred while loading the game data")}
            </div>
          </div>
        )}

        {!isLoading && !error && rows.length > 0 && (
          <GameDataTable
            playersInfos={rows as any}
            setEditableData={() => {}}
          />
        )}

        {!isLoading && !error && rows.length === 0 && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            <p className="text-muted-foreground">No player data available for this game.</p>
          </div>
        )}
      </div>
    </div>
  );
}
