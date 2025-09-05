import React, { useEffect, useMemo, useState } from "react";
import { PlayerInfo } from "../../../entities/game/types";
import { useGetGame } from "../api/getSession";
import { useUploadGame } from "../api/uploadSession";
import GameUrlForm from "../components/SessionUrlForm";
import GameStatusCard from "../components/SessionStatusCard";
import GameSummaryTiles from "../components/SessionSummaryTiles";
import GameDataTable from "../components/IngestDataTable";
import GameActionBar from "../components/SessionActionBar";
import { deriveTotals } from "../lib/deriveTotals";
import { formatErrorMessage } from "../lib/validation";
import { useLocation, useParams } from "react-router-dom";
import { useAdminSession } from "../../../contexts/AdminSessionContext";
import { useToast } from "../../../contexts/ToastContext";
import { useGameTitle } from "../../../shared/hooks/useGameTitle";

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
  const [gameNumber, setGameNumber] = useState<string>("");
  
  // Get public code from URL params and admin session context
  const { publicCode } = useParams<{ publicCode: string }>();
  const { adminCode } = useAdminSession();
  const { showSuccess, showError, showInfo } = useToast();
  const { title } = useGameTitle(publicCode || '');
  
  // Ensure we have required codes
  if (!publicCode) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Invalid Game Code</h1>
          <p className="text-gray-600">No public game code found in URL.</p>
        </div>
      </div>
    );
  }
  
  if (!adminCode) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Admin Access Required</h1>
          <p className="text-gray-600">You need to be logged in as admin to access this page.</p>
        </div>
      </div>
    );
  }
  
  const PUBLIC_CODE = publicCode;
  const ADMIN_CODE = adminCode;

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

  // Handle upload success/error with toast notifications
  useEffect(() => {
    if (upload.isSuccess) {
      showSuccess(
        "Upload Successful!",
        "Session has been saved to the database successfully.",
        5000
      );
    }
  }, [upload.isSuccess, showSuccess]);

  useEffect(() => {
    if (upload.isError) {
      const errorMessage = formatErrorMessage(upload.error);
      showError(
        "Upload Failed",
        errorMessage || "There was an error uploading the session. Please try again.",
        7000 // Show errors longer
      );
    }
  }, [upload.isError, upload.error, showError]);

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
    // Show info toast when upload starts
    showInfo("Upload Started", "Processing your session data...", 3000);
    
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
      gameNumber: gameNumber ? parseInt(gameNumber) : undefined,
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
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Submit Game Session</h1>
          <p className="mt-2 text-gray-600">
            Import PokerNow session data for game <span className="font-mono bg-gray-100 px-2 py-1 rounded">{title}</span>
          </p>
        </div>

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
              <GameDataTable playersInfos={rows} setEditableData={setRows} publicCode={PUBLIC_CODE} />
              
              <div className="bg-white rounded-lg border shadow-sm">
                <div className="border-b p-4">
                  <h3 className="text-lg font-semibold">Optional Settings</h3>
                </div>
                <div className="p-4">
                  <div className="bg-yellow-50 border-l-4 border-yellow-400 rounded p-4">
                    <div className="flex items-start">
                      <div className="flex-shrink-0">
                        <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="ml-3 flex-1">
                        <h4 className="font-medium text-yellow-800">Manual Game Number Override</h4>
                        <div className="mt-2 text-sm text-yellow-700">
                          <p>Leave blank to auto-assign the next game number, or enter a specific number to override (useful for re-uploading deleted games).</p>
                        </div>
                        <div className="mt-3">
                          <label htmlFor="gameNumber" className="block text-sm font-medium text-gray-700 mb-1">
                            Game Number
                          </label>
                          <input
                            type="number"
                            id="gameNumber"
                            value={gameNumber}
                            onChange={(e) => setGameNumber(e.target.value)}
                            placeholder="Auto-assign"
                            min="1"
                            className="block w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <GameActionBar
                onCancel={resetRowsToFetched}
                onUpload={handleUpload}
                balanced={totals.balanced}
                isLoading={upload.isLoading}
                isSuccess={upload.isSuccess}
              />
            </>
          )}
        </div>
      )}
      </div>
    </div>
  );
}
