import { usePlayerSummaries } from "../api/getPlayerSummaries";
import { PlayerSummaryRow } from "../../../entities/game/types";
import GameDataTable from "../components/GameDataTable";

interface GameSummaryPageProps {
  publicCode: string;
}

export default function GameSummaryPage({ publicCode }: GameSummaryPageProps) {
  const { data, isLoading, error } = usePlayerSummaries(publicCode);
  const rows: PlayerSummaryRow[] = data?.rows || [];
  const title = data?.title?.trim() ? data.title : publicCode;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Game Summary</h1>
          <p className="mt-2 text-gray-600">
            Player statistics for <span className="font-mono bg-gray-100 px-2 py-1 rounded">{title}</span>
          </p>
        </div>
        
        {isLoading && (
          <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
            Loading...
          </div>
        )}
        
{!!error && (
          <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400 rounded">
            <div className="text-red-800 font-medium">Error</div>
            <div className="text-red-700">
              {String(error instanceof Error ? error.message : "An error occurred while loading the game data")}
            </div>
          </div>
        )}
        
        {!isLoading && !error && (
          <GameDataTable
            playersInfos={rows as any}
            setEditableData={() => {}}
          />
        )}
      </div>
    </div>
  );
}
