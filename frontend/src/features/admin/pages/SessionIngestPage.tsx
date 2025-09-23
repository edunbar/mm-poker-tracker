import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useAdminSession } from "../../../contexts/AdminSessionContext";
import { useToast } from "../../../contexts/ToastContext";
import { PlayerInfo } from "../../../entities/game/types";
import { useGameTitle } from "../../../shared/hooks/useGameTitle";
import { Heading, Text } from "../../../shared/ui/typography";
import { useGetGame } from "../api/getSession";
import { useUploadGame } from "../api/uploadSession";
import GameDataTable from "../components/IngestDataTable";
import GameActionBar from "../components/SessionActionBar";
import GameStatusCard from "../components/SessionStatusCard";
import GameSummaryTiles from "../components/SessionSummaryTiles";
import GameUrlForm from "../components/SessionUrlForm";
import { deriveTotals } from "../lib/deriveTotals";
import { formatErrorMessage } from "../lib/validation";
import { Button } from "../../../shared/ui/button";
import { GitMerge, ChevronDown, HelpCircle } from "lucide-react";

interface GameDataTableProps {
  playersInfos: PlayerInfo[];
  setEditableData: React.Dispatch<React.SetStateAction<PlayerInfo[]>>;
}

export default function GameIngestPage() {
  const [gameUrl, setGameUrl] = useState("");
  const [submittedUrl, setSubmittedUrl] = useState("");
  const [rows, setRows] = useState<GameDataTableProps["playersInfos"]>([]);
  const [date, setDate] = useState<string>("");
  const [gameNumber, setGameNumber] = useState<string>("");
  const [mergeMode, setMergeMode] = useState(false);
  const [selectedPlayers, setSelectedPlayers] = useState<Set<number>>(new Set());
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [targetPlayerIndex, setTargetPlayerIndex] = useState<number | null>(null);
  const [mergingPlayers, setMergingPlayers] = useState(false);
  const [showOptionalSettings, setShowOptionalSettings] = useState(false);
  const [hoveredTooltip, setHoveredTooltip] = useState<string | null>(null);

  // Get public code from URL params and admin session context
  const { publicCode } = useParams<{ publicCode: string }>();
  const { adminCode } = useAdminSession();
  const { showSuccess, showError, showInfo } = useToast();
  const { title: _title } = useGameTitle(publicCode || '');

  // All hooks must be called before any conditional returns
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

  // Ensure we have required codes
  if (!publicCode) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Heading variant="h2" className="mb-2">Invalid Game Code</Heading>
          <Text variant="body" color="muted">No public game code found in URL.</Text>
        </div>
      </div>
    );
  }
  
  if (!adminCode) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Heading variant="h2" className="mb-2">Admin Access Required</Heading>
          <Text variant="body" color="muted">You need to be logged in as admin to access this page.</Text>
        </div>
      </div>
    );
  }
  
  const PUBLIC_CODE = publicCode;
  const ADMIN_CODE = adminCode;

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
      ...(date && { date: `${date}T00:00:00Z` }),
      ...(gameNumber && { gameNumber: parseInt(gameNumber) }),
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

  const togglePlayerSelection = (index: number) => {
    const newSelection = new Set(selectedPlayers);
    if (newSelection.has(index)) {
      newSelection.delete(index);
    } else {
      newSelection.add(index);
    }
    setSelectedPlayers(newSelection);
  };

  const startMergeMode = () => {
    setMergeMode(true);
    setSelectedPlayers(new Set());
  };

  const cancelMergeMode = () => {
    setMergeMode(false);
    setSelectedPlayers(new Set());
    setTargetPlayerIndex(null);
  };

  const handleMergePlayers = async () => {
    if (selectedPlayers.size < 2 || targetPlayerIndex === null) return;

    setMergingPlayers(true);
    const selectedIndices = Array.from(selectedPlayers);
    const targetPlayer = rows[targetPlayerIndex];

    if (!targetPlayer) {
      setMergingPlayers(false);
      return;
    }

    const mergedPlayer: PlayerInfo = {
      ...targetPlayer,
      buyInSum: 0,
      buyOutSum: 0,
      inGame: 0,
      names: [],
    };

    selectedIndices.forEach(index => {
      const player = rows[index];
      if (!player) return;

      mergedPlayer.buyInSum += player.buyInSum || 0;
      mergedPlayer.buyOutSum += player.buyOutSum || 0;
      mergedPlayer.inGame += player.inGame || 0;
      if (player.names) {
        mergedPlayer.names = [...mergedPlayer.names, ...player.names];
      }
    });

    mergedPlayer.names = Array.from(new Set(mergedPlayer.names));
    const buyOutEffective = mergedPlayer.buyOutSum === 0 ? mergedPlayer.inGame : mergedPlayer.buyOutSum;
    mergedPlayer.net = buyOutEffective - mergedPlayer.buyInSum;

    const newPlayersInfos = rows.filter((_, index) => !selectedPlayers.has(index));
    newPlayersInfos.push(mergedPlayer);

    setRows(newPlayersInfos);
    setSelectedPlayers(new Set());
    setTargetPlayerIndex(null);
    setShowMergeModal(false);
    setMergingPlayers(false);
    setMergeMode(false);
  };

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-8">
          <Heading variant="h1">Submit Game Session</Heading>
          <Text variant="body" color="muted" className="mt-2">
            Import PokerNow session data
          </Text>
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

          {game.isLoading && <Text variant="body">Loading game data...</Text>}
          {game.isError && (
            <Text variant="body" color="destructive">Error loading game data.</Text>
          )}

          {rows.length > 0 && (
            <>
              <GameSummaryTiles
                buyInTotal={totals.buyInTotal}
                cashOutTotal={totals.cashOutTotal}
                net={totals.net}
              />
              <GameDataTable
                playersInfos={rows}
                setEditableData={setRows}
                publicCode={PUBLIC_CODE}
                mergeMode={mergeMode}
                selectedPlayers={selectedPlayers}
                onPlayerSelect={togglePlayerSelection}
              />

              {/* Merge Mode Banner */}
              {mergeMode ? (
                <div className="p-4 bg-blue-50 dark:bg-blue-950 border-2 border-blue-300 dark:border-blue-700 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <GitMerge className="h-6 w-6 text-blue-600 dark:text-blue-400 mt-0.5" />
                      <div>
                        <h3 className="text-base font-semibold text-blue-900 dark:text-blue-100 mb-1">
                          Merge Mode Active
                        </h3>
                        <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">
                          Click on player rows above to select duplicates for merging. Select at least 2 players.
                        </p>
                        {selectedPlayers.size > 0 && (
                          <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                            {selectedPlayers.size} {selectedPlayers.size === 1 ? 'player' : 'players'} selected
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={cancelMergeMode}
                        variant="outline"
                        size="sm"
                      >
                        Cancel
                      </Button>
                      {selectedPlayers.size >= 2 && (
                        <Button
                          onClick={() => {
                            setTargetPlayerIndex(Array.from(selectedPlayers)[0] ?? null);
                            setShowMergeModal(true);
                          }}
                          variant="default"
                          size="sm"
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          Continue to Merge
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-accent/50 border border-border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <GitMerge className="h-5 w-5 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      Have duplicate players? Click to merge them
                    </span>
                  </div>
                  <Button
                    onClick={startMergeMode}
                    variant="outline"
                    size="sm"
                    className="border-blue-300 text-blue-700 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-950"
                  >
                    <GitMerge className="h-4 w-4 mr-2" />
                    Start Merge Mode
                  </Button>
                </div>
              )}

              <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
                <button
                  onClick={() => setShowOptionalSettings(!showOptionalSettings)}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-accent/50 transition-colors"
                >
                  <Text variant="body" weight="semibold">Optional Settings</Text>
                  <ChevronDown
                    className={`h-4 w-4 text-muted-foreground transition-transform ${
                      showOptionalSettings ? 'transform rotate-180' : ''
                    }`}
                  />
                </button>

                {showOptionalSettings && (
                  <div className="border-t border-border px-4 py-3 space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        <Text variant="bodySmall" weight="medium" as="label" htmlFor="gameNumber" className="whitespace-nowrap">
                          Game Number
                        </Text>
                        <div
                          className="relative cursor-help"
                          onMouseEnter={() => setHoveredTooltip('gameNumber')}
                          onMouseLeave={() => setHoveredTooltip(null)}
                        >
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                          {hoveredTooltip === 'gameNumber' && (
                            <div className="absolute left-6 top-0 w-64 p-2 bg-popover text-popover-foreground text-xs rounded-lg shadow-lg border border-border z-10">
                              Leave blank to auto-assign the next game number, or enter a specific number to override (useful for re-uploading deleted games)
                            </div>
                          )}
                        </div>
                      </div>
                      <input
                        type="number"
                        id="gameNumber"
                        value={gameNumber}
                        onChange={(e) => setGameNumber(e.target.value)}
                        placeholder="Auto-assign"
                        min="1"
                        className="w-32 px-3 py-1.5 border border-input bg-background text-foreground text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        <Text variant="bodySmall" weight="medium" as="label" htmlFor="gameDate" className="whitespace-nowrap">
                          Game Date
                        </Text>
                        <div
                          className="relative cursor-help"
                          onMouseEnter={() => setHoveredTooltip('gameDate')}
                          onMouseLeave={() => setHoveredTooltip(null)}
                        >
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                          {hoveredTooltip === 'gameDate' && (
                            <div className="absolute left-6 top-0 w-64 p-2 bg-popover text-popover-foreground text-xs rounded-lg shadow-lg border border-border z-10">
                              Leave blank to use today's date, or select a specific date for this game session
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex-1">
                        <div
                          className="relative w-48"
                          onClick={() => {
                            const input = document.getElementById('gameDate') as HTMLInputElement;
                            if (input && typeof input.showPicker === 'function') {
                              input.showPicker();
                            }
                          }}
                        >
                          <input
                            type="date"
                            id="gameDate"
                            value={date}
                            onChange={(e) => setDate(e.target.value)}
                            className="w-full px-3 py-1.5 border border-input bg-background text-foreground text-sm rounded-md cursor-pointer"
                          />
                        </div>
                        {date && (() => {
                          const parts = date.split('-');
                          const year = parts[0];
                          const month = parts[1];
                          const day = parts[2];
                          if (!year || !month || !day) return null;
                          const dateStr = new Date(Date.UTC(parseInt(year), parseInt(month) - 1, parseInt(day))).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' });
                          return (
                            <Text variant="caption" color="muted" className="mt-0.5 block">
                              {dateStr}
                            </Text>
                          );
                        })()}
                      </div>
                    </div>
                  </div>
                )}
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

      {/* Merge Confirmation Modal */}
      {showMergeModal && selectedPlayers.size >= 2 && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border border-border w-[500px] shadow-lg rounded-md bg-card text-card-foreground">
            <div className="mt-3">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900">
                <GitMerge className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-lg leading-6 font-medium text-foreground mt-4 text-center">Merge Players</h3>
              <div className="mt-4 px-4">
                <p className="text-sm text-muted-foreground mb-3">
                  Select which player to merge into (this player's ID and name will be kept):
                </p>
                <div className="bg-muted rounded-lg p-3 space-y-2 text-sm mb-4">
                  {Array.from(selectedPlayers).map(index => {
                    const player = rows[index];
                    if (!player) return null;

                    return (
                      <div
                        key={index}
                        onClick={() => setTargetPlayerIndex(index)}
                        className={`flex items-center justify-between border-b border-border pb-2 last:border-0 cursor-pointer rounded px-2 py-1 transition-colors ${
                          targetPlayerIndex === index
                            ? 'bg-blue-100 dark:bg-blue-900 ring-2 ring-blue-500'
                            : 'hover:bg-accent'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            checked={targetPlayerIndex === index}
                            onChange={() => setTargetPlayerIndex(index)}
                            className="w-4 h-4 text-blue-600"
                          />
                          <div>
                            <div className="font-medium">{player.validated_name || player.names?.[0] || 'Unknown'}</div>
                            <div className="text-xs text-muted-foreground">ID: {player.id || 'N/A'} • {player.names?.join(', ')}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">${(player.buyInSum || 0).toFixed(2)}</div>
                          <div className="text-xs text-muted-foreground">Buy-in</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="bg-muted rounded-lg p-3 mb-3">
                  <div className="text-sm font-medium mb-2">Merge Summary:</div>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <div>• <strong>{selectedPlayers.size} players</strong> will be combined</div>
                    <div>• Total buy-in: <strong>${Array.from(selectedPlayers).reduce((sum, idx) => sum + (rows[idx]?.buyInSum || 0), 0).toFixed(2)}</strong></div>
                    <div>• All player names will be combined and deduplicated</div>
                    {targetPlayerIndex !== null && (
                      <div className="mt-2 pt-2 border-t border-border text-blue-600 dark:text-blue-400">
                        → Merging into: <strong>{rows[targetPlayerIndex]?.validated_name || rows[targetPlayerIndex]?.names?.[0] || 'Unknown'}</strong>
                      </div>
                    )}
                  </div>
                </div>
                <div className="p-3 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-sm text-yellow-900 dark:text-yellow-100">
                    <strong>Important:</strong> The selected target player's ID and verified name will be kept. All other players will be removed after merging.
                  </p>
                </div>
              </div>
              <div className="items-center px-4 py-3 mt-4">
                <div className="flex space-x-2">
                  <Button
                    onClick={() => {
                      setShowMergeModal(false);
                      setTargetPlayerIndex(null);
                    }}
                    variant="outline"
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleMergePlayers}
                    disabled={mergingPlayers || targetPlayerIndex === null}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {mergingPlayers ? 'Merging...' : targetPlayerIndex === null ? 'Select Target Player' : 'Confirm Merge'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
