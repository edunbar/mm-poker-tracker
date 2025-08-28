import React, { useEffect, useMemo, useState } from "react";
import { PlayerInfo } from "../../../entities/game/types";
import { useGetGame } from "../api/getGame";
import { useUploadGame } from "../api/uploadGame";
import GameUrlForm from "../components/GameUrlForm";
import GameStatusCard from "../components/GameStatusCard";
import GameSummaryTiles from "../components/GameSummaryTiles";
import GameDataTable from "../components/IngestDataTable";
import GameActionBar from "../components/GameActionBar";
import { deriveTotals } from "../lib/deriveTotals";
import { formatErrorMessage } from "../lib/validation";
import { useLocation } from "react-router-dom";

interface GameDataTableProps {
  playersInfos: PlayerInfo[];
  setEditableData: React.Dispatch<React.SetStateAction<PlayerInfo[]>>;
}

function useQuery() {
  return new URLSearchParams(useLocation().search);
}
export default function GameIngestPage() {
  const [gameUrl, setGameUrl] = useState("");
  const [submittedUrl, setSubmittedUrl] = useState("");
  const [rows, setRows] = useState<GameDataTableProps["playersInfos"]>([]);
  const [date, setDate] = useState<string>("");

  // Use .env values for public_code and admin_code
  const PUBLIC_CODE = process.env.REACT_APP_PUBLIC_CODE || "C4QROK";
  const ADMIN_CODE =
    process.env.REACT_APP_ADMIN_CODE ||
    "2LT8wByw4sMLAwB_ISq2TMRwJ6zaUZ1oy4w7y4WQscE";

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
    // Extract sessionId from submittedUrl after '/games/'
    let sessionId = "";
    const match = submittedUrl.match(/\/games\/([^/?#]+)/);
    if (match && match[1]) {
      sessionId = match[1];
    }
    // Always send the latest edited rows as game_data
    const game_data = { playersInfos: rows };
    upload.mutate({
      public_code: PUBLIC_CODE,
      admin_code: ADMIN_CODE,
      sessionId,
      game_data,
      date,
    });
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
