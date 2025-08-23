import React, { useEffect, useMemo, useState } from "react";
import { PlayerInfo } from "../../../entities/game/types";
import { useGetGame } from "../api/getGame";
import { useUploadGame } from "../api/uploadGame";
import GameUrlForm from "../components/GameUrlForm";
import GameStatusCard from "../components/GameStatusCard";
import GameSummaryTiles from "../components/GameSummaryTiles";
import GameDataTable from "../components/GameDataTable";
import GameActionBar from "../components/GameActionBar";
import { deriveTotals } from "../lib/deriveTotals";
import { formatErrorMessage } from "../lib/validation";

interface GameDataTableProps {
  playersInfos: PlayerInfo[];
  setEditableData: React.Dispatch<React.SetStateAction<PlayerInfo[]>>;
}

export default function GameIngestPage() {
  const [gameUrl, setGameUrl] = useState("");
  const [submittedUrl, setSubmittedUrl] = useState("");
  const [rows, setRows] = useState<GameDataTableProps["playersInfos"]>([]);

  const game = useGetGame(submittedUrl);
  const upload = useUploadGame();

  useEffect(() => {
    if (game.data?.playersInfos) {
      // normalize playersInfos to array
      const pi = game.data.playersInfos;
      const arr: GameDataTableProps["playersInfos"] = Array.isArray(pi)
        ? pi
        : pi && typeof pi === "object"
        ? Object.values(pi)
        : [];
      setRows(arr);
    }
  }, [game.data]);

  const totals = useMemo(() => deriveTotals(rows), [rows]);

  const status: "success" | "error" | null = upload.isSuccess
    ? "success"
    : upload.isError
    ? "error"
    : null;

  const errorMessage = upload.isError ? formatErrorMessage(upload.error) : null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittedUrl(gameUrl);
    upload.reset();
  };

  const handleUpload = () => {
    upload.mutate(rows);
  };

  const resetRowsToFetched = () => {
    const pi = game.data?.playersInfos;
    const arr: GameDataTableProps["playersInfos"] = Array.isArray(pi)
      ? pi
      : pi && typeof pi === "object"
      ? Object.values(pi)
      : [];
    setRows(arr);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto py-8 px-4">
      <h2 className="text-2xl font-bold">Submit PokerNow Game URL</h2>

      <GameUrlForm
        gameUrl={gameUrl}
        setGameUrl={setGameUrl}
        handleSubmit={handleSubmit}
        isLoading={game.isLoading}
      />

      {submittedUrl && (
        <div className="game-data space-y-6">
          <GameStatusCard
            status={status}
            balanced={totals.balanced}
            errorMessage={errorMessage}
          />

          {game.isLoading && <p>Loading game data...</p>}
          {game.isError && (
            <p className="text-red-600">Error loading game data.</p>
          )}

          {rows.length > 0 && (
            <>
              <GameSummaryTiles
                buyInTotal={totals.buyInTotal}
                cashOutTotal={totals.cashOutTotal}
                net={totals.net}
              />
              <GameDataTable playersInfos={rows} setEditableData={setRows} />
              <GameActionBar
                onCancel={resetRowsToFetched}
                onUpload={handleUpload}
                balanced={totals.balanced}
                isLoading={upload.isLoading}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}
