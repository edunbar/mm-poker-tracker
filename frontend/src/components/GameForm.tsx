import React, { useState, useEffect } from "react";
import useGameQuery from "../hooks/useGameQuery";
import { useMutation } from "react-query";
import { uploadGameToSheets } from "../api/game";
import GameDataTable from "./GameDataTable";
import GameTotals from "./GameTotals";

const GameForm: React.FC = () => {
  const uploadMutation = useMutation(uploadGameToSheets);

  const [gameUrl, setGameUrl] = useState("");
  const [submittedUrl, setSubmittedUrl] = useState("");
  const [editableData, setEditableData] = useState<any[]>([]);

  const { data, isLoading, isError } = useGameQuery(submittedUrl);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setSubmittedUrl(gameUrl);
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
                uploadMutation.mutate(editableData, {
                  onSuccess: () => alert("Upload to Google Sheets triggered."),
                  onError: () => alert("Failed to upload to Google Sheets."),
                });
              }}
              disabled={uploadMutation.isLoading}
            >
              {uploadMutation.isLoading ? "Uploading..." : "Upload"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GameForm;
