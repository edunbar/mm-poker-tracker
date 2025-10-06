import { ChevronDown, GitMerge, HelpCircle, X } from "lucide-react";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useAdminSession } from "../../../contexts/AdminSessionContext";
import { useAuth } from "../../../contexts/AuthContext";
import { useToast } from "../../../contexts/ToastContext";
import { PlayerInfo } from "../../../entities/game/types";
import { useGameTitle } from "../../../shared/hooks/useGameTitle";
import { Button } from "../../../shared/ui/button";
import { Heading, Text } from "../../../shared/ui/typography";
import { useGetGame } from "../api/getSession";
import { useUploadHandLog } from "../api/uploadHandLog";
import { useUploadGame } from "../api/uploadSession";
import HandLogUpload from "../components/HandLogUpload";
import GameDataTable from "../components/IngestDataTable";
import PlayerMappingModal from "../components/PlayerMappingModal";
import GameActionBar from "../components/SessionActionBar";
import GameStatusCard from "../components/SessionStatusCard";
import GameUrlForm from "../components/SessionUrlForm";
import { deriveTotals } from "../lib/deriveTotals";
import { formatErrorMessage } from "../lib/validation";

interface GameDataTableProps {
  playersInfos: PlayerInfo[];
  setEditableData: React.Dispatch<React.SetStateAction<PlayerInfo[]>>;
}

interface ApiError {
  message?: string;
}

interface UnmatchedPlayer {
  display_name: string;
  external_id: string | null;
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
  const [csvViewerOpen, setCsvViewerOpen] = useState(false);
  const [handLogFile, setHandLogFile] = useState<File | null>(null);
  const [uploadedSessionId, setUploadedSessionId] = useState<string | null>(null);
  const [handLogUploadStatus, setHandLogUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'needs_mapping' | 'error'>('idle');
  const [unmatchedPlayers, setUnmatchedPlayers] = useState<UnmatchedPlayer[]>([]);
  const [showPlayerMapping, setShowPlayerMapping] = useState(false);
  const [handLogError, setHandLogError] = useState<string>('');
  const [handLogResult, setHandLogResult] = useState<{ events_created?: number; hands_created?: number; total_hands?: number }>({});
  const handLogUploadTriggered = useRef(false);

  // Get public code from URL params and admin session context
  const { publicCode } = useParams<{ publicCode: string }>();
  const { adminCode } = useAdminSession();
  const { isAuthenticated, user } = useAuth();
  const { showSuccess, showError, showInfo } = useToast();
  const { title: _title } = useGameTitle(publicCode || '');

  // All hooks must be called before any conditional returns
  const game = useGetGame(submittedUrl);
  const upload = useUploadGame();
  const uploadHandLog = useUploadHandLog();

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
    if (upload.isSuccess && upload.data?.session_id && !handLogUploadTriggered.current) {
      showSuccess(
        "Upload Successful!",
        "Session has been saved to the database successfully.",
        5000
      );

      const sessionId = upload.data.session_id;
      setUploadedSessionId(sessionId);

      // If hand log file is selected, automatically upload it (only once)
      if (handLogFile && publicCode) {
        handLogUploadTriggered.current = true;
        setHandLogUploadStatus('uploading');
        uploadHandLog.mutateAsync({
          publicCode,
          sessionId,
          file: handLogFile,
        })
          .then((result) => {
            if (result.status === 'needs_mapping') {
              setUnmatchedPlayers(result.unmatched_players || []);
              setShowPlayerMapping(true);
              setHandLogUploadStatus('needs_mapping');
            } else if (result.status === 'success') {
              setHandLogUploadStatus('success');
              setHandLogResult(result);
              showSuccess(
                'Hand Log Uploaded!',
                `${result.events_created} events from ${result.hands_created} hands imported successfully.`,
                5000
              );
            }
          })
          .catch((error) => {
            setHandLogUploadStatus('error');
            setHandLogError((error as ApiError).message || 'Failed to upload hand log');
            showError('Upload Failed', (error as ApiError).message || 'Failed to upload hand log');
          });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [upload.isSuccess, upload.data?.session_id]);

  useEffect(() => {
    if (upload.isError) {
      const error = upload.error as any;

      // Handle 403 specifically when authenticated
      if (isAuthenticated && error?.response?.status === 403) {
        showError(
          "Access Denied",
          "You don't own this game. Please claim it first or use the admin code.",
          7000
        );
        return;
      }

      const errorMessage = formatErrorMessage(upload.error);
      showError(
        "Upload Failed",
        errorMessage || "There was an error uploading the session. Please try again.",
        7000 // Show errors longer
      );
    }
  }, [upload.isError, upload.error, showError, isAuthenticated]);

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

  // If not authenticated, require admin code
  if (!isAuthenticated && !adminCode) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Heading variant="h2" className="mb-2">Admin Access Required</Heading>
          <Text variant="body" color="muted">You need to be logged in as admin or authenticated to access this page.</Text>
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
    // Reset hand log upload trigger
    handLogUploadTriggered.current = false;

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
      // Only send admin_code when not authenticated
      ...(!isAuthenticated && ADMIN_CODE && { admin_code: ADMIN_CODE }),
      sessionId,
      game_data,
      ...(date && { date: `${date}T00:00:00Z` }),
      ...(gameNumber && { gameNumber: parseInt(gameNumber) }),
      ...(game.data?.ledger_csv?.content && { ledger_csv_content: game.data.ledger_csv.content }),
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

  const handleHandLogFileSelect = (file: File) => {
    setHandLogFile(file);
    setHandLogUploadStatus('idle');
    setHandLogError('');
  };

  const handlePlayerMappingConfirm = async (mappings: Record<string, string>) => {
    if (!handLogFile || !uploadedSessionId || !publicCode) return;

    setShowPlayerMapping(false);
    setHandLogUploadStatus('uploading');

    try {
      const result = await uploadHandLog.mutateAsync({
        publicCode,
        sessionId: uploadedSessionId,
        file: handLogFile,
        playerMappings: mappings,
      });

      if (result.status === 'success') {
        setHandLogUploadStatus('success');
        setHandLogResult(result);
        showSuccess(
          'Hand Log Uploaded!',
          `${result.events_created} events from ${result.hands_created} hands imported successfully.`,
          5000
        );
      }
    } catch (error) {
      setHandLogUploadStatus('error');
      setHandLogError((error as ApiError).message || 'Failed to upload hand log');
      showError('Upload Failed', (error as ApiError).message || 'Failed to upload hand log');
    }
  };

  const handleClearHandLog = () => {
    setHandLogFile(null);
    setHandLogUploadStatus('idle');
    setHandLogError('');
    setHandLogResult({});
  };

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4 md:px-6 lg:px-8">

        <div className="mb-8">
          <Heading variant="h1">Submit Game Session</Heading>
          <Text variant="body" color="muted" className="mt-2">
            Import PokerNow session data
          </Text>
          {isAuthenticated && user && (
            <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md">
              <Text variant="bodySmall" className="text-blue-800 dark:text-blue-200">
                Uploading as: <strong>{user.email}</strong>
              </Text>
            </div>
          )}
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
            ledgerCsvStatus={game.data?.ledger_csv || null}
            onViewCsv={() => setCsvViewerOpen(true)}
          />

          {rows.length > 0 && (
            <HandLogUpload
              onFileSelect={handleHandLogFileSelect}
              uploadStatus={handLogUploadStatus}
              uploadResult={handLogResult}
              error={handLogError}
              onClearFile={handleClearHandLog}
            />
          )}

          {game.isLoading && <Text variant="body">Loading game data...</Text>}
          {game.isError && (
            <Text variant="body" color="destructive">Error loading game data.</Text>
          )}

          {rows.length > 0 && (
            <>
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
                    <strong>Important:</strong> The selected target player's ID and name will be kept. All other players will be removed after merging.
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

      {/* CSV Viewer Modal */}
      {csvViewerOpen && game.data?.ledger_csv?.content && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-border">
              <div>
                <Heading variant="h3">Ledger CSV</Heading>
                <Text variant="caption" color="muted" className="mt-1">PokerNow Historical Data</Text>
              </div>
              <Button
                onClick={() => setCsvViewerOpen(false)}
                variant="ghost"
                size="icon-sm"
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            <div className="flex-1 overflow-auto p-6">
              <div className="bg-muted rounded-md p-4 overflow-x-auto">
                <table className="min-w-full text-sm font-mono">
                  <tbody>
                    {game.data.ledger_csv.content.split('\n').map((row: string, rowIndex: number) => {
                      const cells = row.split(',');
                      const isHeader = rowIndex === 0;
                      return (
                        <tr key={rowIndex} className={isHeader ? 'font-bold border-b-2 border-border' : 'border-b border-border/50'}>
                          {cells.map((cell: string, cellIndex: number) => (
                            <td
                              key={cellIndex}
                              className={`px-3 py-2 ${isHeader ? 'text-foreground' : 'text-muted-foreground'}`}
                            >
                              {cell.replace(/^"(.*)"$/, '$1')}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex justify-end p-6 border-t border-border">
              <Button
                onClick={() => setCsvViewerOpen(false)}
                variant="outline"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Player Mapping Modal */}
      {showPlayerMapping && (
        <PlayerMappingModal
          unmatchedPlayers={unmatchedPlayers}
          existingPlayers={rows.map(row => ({
            id: row.id || '',
            display_name: row.validated_name || row.names?.[0] || '',
            external_id: row.id
          }))}
          onConfirm={handlePlayerMappingConfirm}
          onCancel={() => {
            setShowPlayerMapping(false);
            setHandLogUploadStatus('idle');
          }}
        />
      )}
      </div>
    </div>
  );
}
