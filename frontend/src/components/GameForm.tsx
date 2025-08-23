import React, { useState, useEffect, useMemo } from "react";
import useGameQuery from "../hooks/useGameQuery";
import { useMutation } from "react-query";
import { uploadGameToSheets } from "../api/game";
import GameDataTable from "./GameDataTable";
import { CheckCircle2, AlertTriangle, Upload, Loader2 } from "lucide-react";

// --- Helper Functions ---
function formatNumber(n: number) {
  return new Intl.NumberFormat().format(n || 0);
}
function isNumeric(value: any) {
  return value !== null && value !== "" && !Number.isNaN(Number(value));
}
function formatErrorMessage(error: any): string {
  if (!error) return "An unknown error occurred.";
  const str = String(error);
  const match = str.match(/"([^"]+)"/);
  if (match && match[1]) return match[1];
  return str;
}

// --- Summary Tiles ---
function SummaryTile({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: string;
}) {
  const accentMap: Record<string, string> = {
    ok: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    pos: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    neg: "bg-red-50 text-red-700 ring-red-200",
    base: "bg-white text-gray-900 ring-gray-200",
  };
  const classes = accent ? accentMap[accent] : accentMap.base;
  return (
    <div className={`shadow-sm ring-1 ${classes} border-none p-4 rounded-lg`}>
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-semibold tracking-tight">
        {formatNumber(value)}
      </div>
    </div>
  );
}

// --- Status Card ---
function StatusCard({
  status,
  balanced,
  errorMessage,
}: {
  status: string | null;
  balanced: boolean;
  errorMessage?: string | null;
}) {
  if (status === "success") {
    return (
      <div className="border-emerald-200 bg-emerald-50 rounded-lg p-4 flex gap-3 items-center">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
        <div>
          <div className="font-semibold text-emerald-700">
            Upload successful
          </div>
          <div className="text-sm">
            Game has been saved to the database and synced to your sheet.
          </div>
        </div>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="border-red-200 bg-red-50 rounded-lg p-4 flex gap-3 items-center">
        <AlertTriangle className="h-5 w-5 text-red-600" />
        <div>
          <div className="font-semibold text-red-700">Upload blocked</div>
          <div className="text-sm">
            Please fix invalid cells and ensure totals are balanced before
            uploading.
          </div>
          {errorMessage && (
            <div className="text-sm text-red-600 mt-2">{errorMessage}</div>
          )}
        </div>
      </div>
    );
  }
  return (
    <div className="bg-white rounded-lg p-4 flex gap-3 items-center">
      {balanced ? (
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
      ) : (
        <AlertTriangle className="h-5 w-5 text-red-600" />
      )}
      <div>
        <div
          className={`font-semibold ${
            balanced ? "text-emerald-700" : "text-red-700"
          }`}
        >
          {balanced ? "Ready to upload" : "Needs attention"}
        </div>
        <div className="text-sm">
          {balanced
            ? "Totals are balanced. You can safely upload this game."
            : "Enter numeric values for Buy In and Cash Out. Net and totals will auto‑recalculate."}
        </div>
      </div>
    </div>
  );
}

// --- Main GameForm ---
const GameForm: React.FC = () => {
  const [gameUrl, setGameUrl] = useState("");
  const [submittedUrl, setSubmittedUrl] = useState("");
  const [editableData, setEditableData] = useState<any[]>([]);
  const [uploadStatus, setUploadStatus] = useState<"success" | "error" | null>(
    null
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const uploadMutation = useMutation(uploadGameToSheets, {
    onSuccess: () => {
      setUploadStatus("success");
      setErrorMessage(null);
    },
    onError: (error: any) => {
      setUploadStatus("error");
      if (error?.response?.data?.error) {
        setErrorMessage(formatErrorMessage(error.response.data.error));
      } else if (error?.message) {
        setErrorMessage(formatErrorMessage(error.message));
      } else {
        setErrorMessage("Failed to upload to Google Sheets.");
      }
    },
  });

  const { data, isLoading, isError } = useGameQuery(submittedUrl);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setSubmittedUrl(gameUrl);
    setUploadStatus(null);
  };

  // Converts playersInfos JSON to array
  const getPlayersInfosArray = (playersInfos: any) => {
    if (Array.isArray(playersInfos)) {
      return playersInfos;
    } else if (playersInfos && typeof playersInfos === "object") {
      return Object.values(playersInfos);
    }
    return [];
  };

  useEffect(() => {
    if (data && data.playersInfos) {
      setEditableData(getPlayersInfosArray(data.playersInfos));
    }
  }, [data]);

  // --- Derived Totals & Validation ---
  const derived = useMemo(() => {
    const buyInTotal = editableData.reduce(
      (sum, p) => sum + Number(p.buyInSum || 0),
      0
    );
    // Add both buyOutSum and inGame for each player
    const cashOutTotal = editableData.reduce(
      (sum, p) => sum + Number(p.buyOutSum || 0) + Number(p.inGame || 0),
      0
    );
    const net = cashOutTotal - buyInTotal;
    const hasInvalid = editableData.some(
      (r) =>
        !isNumeric(r.buyInSum) ||
        !isNumeric(r.buyOutSum) ||
        !isNumeric(r.inGame)
    );
    return { buyInTotal, cashOutTotal, net, hasInvalid };
  }, [editableData]);
  const balanced = derived.net === 0 && !derived.hasInvalid;

  // --- Upload Handler ---
  const handleUpload = () => {
    setUploadStatus(null);
    uploadMutation.mutate(editableData);
  };

  // --- UI ---
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h2 className="text-2xl font-bold mb-4">Submit PokerNow Game URL</h2>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-6">
        <input
          type="text"
          id="game_url"
          value={gameUrl}
          onChange={(e) => setGameUrl(e.target.value)}
          required
          placeholder="https://www.pokernow.club/games/your-game-id"
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          {isLoading ? "Loading..." : "Fetch"}
        </button>
      </form>
      {submittedUrl && (
        <div className="game-data space-y-6">
          <StatusCard
            status={uploadStatus}
            balanced={balanced}
            errorMessage={errorMessage}
          />
          {isLoading && <p>Loading game data...</p>}
          {isError && <p className="text-red-600">Error loading game data.</p>}
          {editableData.length > 0 && (
            <>
              {/* Summary Tiles */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                <SummaryTile label="Buy In Total" value={derived.buyInTotal} />
                <SummaryTile
                  label="Cash Out Total"
                  value={derived.cashOutTotal}
                />
                <SummaryTile
                  label="Net"
                  value={derived.net}
                  accent={
                    derived.net === 0 ? "ok" : derived.net > 0 ? "pos" : "neg"
                  }
                />
              </div>
              {/* Editable Table */}
              <GameDataTable
                playersInfos={editableData}
                setEditableData={setEditableData}
              />
              {/* Action Bar */}
              <div className="mt-6 flex items-center justify-between">
                <button
                  className="bg-gray-200 px-4 py-2 rounded"
                  onClick={() =>
                    setEditableData(getPlayersInfosArray(data.playersInfos))
                  }
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  className={`px-4 py-2 rounded text-white flex items-center gap-2 ${
                    balanced && !uploadMutation.isLoading
                      ? "bg-green-600 hover:bg-green-700"
                      : "bg-gray-400 cursor-not-allowed"
                  }`}
                  onClick={handleUpload}
                  disabled={!balanced || uploadMutation.isLoading}
                >
                  {uploadMutation.isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" /> Uploading
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4" /> Upload to Database
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default GameForm;
