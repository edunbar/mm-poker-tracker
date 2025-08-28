import React from "react";
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
    <div className="w-full px-6 py-8">
      <h2 className="text-2xl font-bold mb-6">Game Summary for {title}</h2>
      <>
        {isLoading && <p>Loading...</p>}
        {error && (
          <p className="text-red-600">
            {typeof error === "string" ? error : String(error)}
          </p>
        )}
      </>
      {!isLoading && !error && (
        <div className="w-full">
          <GameDataTable
            playersInfos={rows as any}
            setEditableData={() => {}}
          />
        </div>
      )}
    </div>
  );
}
