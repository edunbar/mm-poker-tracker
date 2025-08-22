import React, { useState, useEffect } from "react";
import useGameQuery from "../hooks/useGameQuery";
import { useMutation } from "react-query";
import { uploadGameToSheets } from "../api/game";
import GameDataTable from "./GameDataTable";
import GameTotals from "./GameTotals";

function formatErrorMessage(error: any): string {
  if (!error) return "An unknown error occurred.";

  const str = String(error);

  // Look for a quoted human-readable message inside the HttpError
  const match = str.match(/"([^"]+)"/);
  if (match && match[1]) {
    return match[1];
  }

  // Otherwise, just return the raw string
  return str;
}

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
      // Use formatErrorMessage for better error display
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
    setUploadStatus(null); // Reset status on new submission
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

  return (
    <div className="game-form">
      <h2>Submit PokerNow Game URL</h2>
      <form onSubmit={handleSubmit}>
        <label htmlFor="game_url">Game URL:</label>
        <input
          type="text"
          id="game_url"
          value={gameUrl}
          onChange={(e) => setGameUrl(e.target.value)}
          required
          placeholder="https://www.pokernow.club/games/your-game-id"
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? "Loading..." : "Submit"}
        </button>
      </form>
      {submittedUrl && (
        <div className="game-data">
          <h3>Game Data</h3>
          {isLoading && <p>Loading game data...</p>}
          {isError && <p>Error loading game data.</p>}
          {editableData.length > 0 && (
            <>
              <GameTotals playersInfos={editableData} />
              <GameDataTable
                playersInfos={editableData}
                setEditableData={setEditableData}
              />
            </>
          )}
          <div
            style={{
              marginTop: "2rem",
              textAlign: "left",
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
            }}
          >
            <div style={{ marginBottom: "1rem" }}>
              Once verification is complete, upload game to Google Sheets:
            </div>
            <button
              style={{
                padding: "0.75rem 1.5rem",
                fontSize: "1rem",
                backgroundColor: "#4caf50",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
              onClick={() => {
                setUploadStatus(null); // Reset status before upload
                uploadMutation.mutate(editableData);
              }}
              disabled={uploadMutation.isLoading}
            >
              {uploadMutation.isLoading ? "Uploading..." : "Upload"}
            </button>
            {uploadStatus === "success" && (
              <div style={{ color: "green", marginTop: "1rem" }}>
                Upload to Google Sheets was successful.
              </div>
            )}
            {uploadStatus === "error" && (
              <div style={{ color: "red", marginTop: "1rem" }}>
                {"Upload Failed: " +
                  (errorMessage ||
                    "Failed to upload to Google Sheets. Please try again.")}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default GameForm;
