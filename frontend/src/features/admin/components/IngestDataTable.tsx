import { AlertTriangle, CheckCircle2, Trash2 } from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import { PlayerInfo } from "../../../entities/game/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../shared/ui/table";
import { deriveTotals } from "../lib/deriveTotals";
import { isNumeric } from "../lib/validation";

function formatNumber(n: number) {
  return new Intl.NumberFormat().format(n || 0);
}

interface GameDataTableProps {
  playersInfos: PlayerInfo[];
  setEditableData: React.Dispatch<React.SetStateAction<PlayerInfo[]>>;
  publicCode: string;
}

const GameDataTable: React.FC<GameDataTableProps> = ({
  playersInfos,
  setEditableData,
  publicCode,
}) => {
  const [verificationStatus, setVerificationStatus] = useState<{[key: string]: {is_verified: boolean, display_name: string | null}}>({});
  const [hoveredPlayer, setHoveredPlayer] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [playerToDelete, setPlayerToDelete] = useState<{ index: number; name: string } | null>(null);

  // Fetch verification status when player data changes
  useEffect(() => {
    const fetchVerificationStatus = async () => {
      const externalIds = playersInfos
        .map(player => player.id)
        .filter(id => id && id.trim() !== '');
      
      if (externalIds.length === 0) return;

      try {
        const response = await fetch(`http://localhost:8000/api/games/${publicCode}/players/check-verification-status`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            external_ids: externalIds
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setVerificationStatus(data);
        }
      } catch {
        // Silently handle verification status fetch errors
      }
    };

    fetchVerificationStatus();
  }, [playersInfos, publicCode]);

  // keep a stable mapping back to original index so edits update correct item
  const sortedPlayers = playersInfos
    .map((player, originalIdx) => ({ ...player, originalIdx }))
    .sort((a, b) => b.net - a.net);

  // Use shared deriveTotals/validation utilities
  const derived = useMemo(() => deriveTotals(playersInfos), [playersInfos]);


  const handleChange = (
    index: number,
    field: keyof PlayerInfo,
    value: string | number | boolean
  ) => {
    const updated = [...playersInfos];
    const target = updated[index];

    if (!target) return;

    if (field === "buyInSum" || field === "buyOutSum") {
      // coerce to number (empty -> NaN will be handled by validation)
      const num = value === "" ? NaN : Number(value);
      target[field] = num as any;

      // recalc per-row net using same rule as UI (if buyOutSum === 0 use inGame)
      const buyOutEffective =
        target.buyOutSum === 0
          ? Number(target.inGame || 0)
          : Number(target.buyOutSum || 0);
      target.net = buyOutEffective - Number(target.buyInSum || 0);
    } else if (field === "net") {
      target.net = Number(value);
    } else if (field === "id") {
      target.id = String(value);
    } else if (field === "names") {
      target.names = (value as string)
        .split(",")
        .map((n) => n.trim())
        .filter((n) => n.length > 0);
    } else if (field === "validated_name") {
      target.validated_name = String(value);
    }

    setEditableData(updated);
  };

  const handleDelete = (indexToDelete: number) => {
    const playerName = playersInfos[indexToDelete]?.validated_name || playersInfos[indexToDelete]?.names?.[0] || `Player ${indexToDelete + 1}`;
    setPlayerToDelete({ index: indexToDelete, name: playerName });
    setShowDeleteConfirm(true);
  };

  const confirmDelete = () => {
    if (playerToDelete) {
      const updated = playersInfos.filter((_, index) => index !== playerToDelete.index);
      setEditableData(updated);
      setShowDeleteConfirm(false);
      setPlayerToDelete(null);
    }
  };

  const cancelDelete = () => {
    setShowDeleteConfirm(false);
    setPlayerToDelete(null);
  };

  if (!Array.isArray(playersInfos) || playersInfos.length === 0) {
    return <div>No player data available.</div>;
  }

  return (
    <div>
      {/* Editable Table */}
      <div className="overflow-auto rounded-xl border border-border bg-card">
        <Table>
          <TableHeader className="bg-muted">
            <TableRow>
              <TableHead className="min-w-[120px]">ID</TableHead>
              <TableHead className="min-w-[170px]">Name</TableHead>
              <TableHead className="w-[80px] text-center">Verified</TableHead>
              <TableHead className="min-w-[220px]">IGN</TableHead>
              <TableHead className="w-[140px] text-right">Buy In</TableHead>
              <TableHead className="w-[140px] text-right">Cash Out</TableHead>
              <TableHead className="w-[120px] text-right">Net</TableHead>
              <TableHead className="w-[80px] text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedPlayers.map((player) => (
              <TableRow
                key={player.id || player.originalIdx}
                className=""
              >
                <TableCell>
                  <input
                    type="text"
                    value={player.id}
                    className="w-full bg-transparent text-foreground outline-none border border-transparent focus:border-input rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(player.originalIdx, "id", e.target.value)
                    }
                  />
                </TableCell>
                <TableCell>
                  <input
                    type="text"
                    value={player.validated_name || ""}
                    className="w-full bg-transparent text-foreground outline-none border border-transparent focus:border-input rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(
                        player.originalIdx,
                        "validated_name",
                        e.target.value
                      )
                    }
                  />
                </TableCell>
                <TableCell className="text-center relative">
                  <div 
                    className="flex items-center justify-center cursor-help relative"
                    onMouseEnter={() => setHoveredPlayer(player.id)}
                    onMouseLeave={() => setHoveredPlayer(null)}
                  >
                    {(() => {
                      const status = verificationStatus[player.id];
                      if (status?.is_verified) {
                        return <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />;
                      } else if (status && !status.is_verified) {
                        return <AlertTriangle className="h-4 w-4 text-sophisticated-gold dark:text-sophisticated-gold" />;
                      } else {
                        return <div className="h-4 w-4 rounded-full bg-muted" />;
                      }
                    })()}
                    
                    {hoveredPlayer === player.id && (
                      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-popover text-popover-foreground text-xs rounded-lg shadow-lg whitespace-nowrap z-10 border border-border">
                        {(() => {
                          const status = verificationStatus[player.id];
                          if (status?.is_verified) {
                            return "Verified player - Admin confirmed identity";
                          } else if (status && !status.is_verified) {
                            return "Unverified player - Exists but not admin verified";
                          } else {
                            return "New player - Will be created on import";
                          }
                        })()}
                        <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-popover" />
                      </div>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <input
                    type="text"
                    value={
                      Array.isArray(player.names)
                        ? player.names.join(", ")
                        : player.names
                    }
                    className="w-full bg-transparent text-foreground outline-none border border-transparent focus:border-input rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(player.originalIdx, "names", e.target.value)
                    }
                  />
                </TableCell>
                <TableCell className="text-right">
                  <input
                    type="number"
                    value={player.buyInSum as any}
                    className={`w-full text-right bg-transparent text-foreground outline-none border rounded-lg px-2 py-1 text-sm ${
                      !isNumeric(player.buyInSum)
                        ? "border-destructive focus:border-destructive"
                        : "border-transparent focus:border-input"
                    }`}
                    onChange={(e) =>
                      handleChange(
                        player.originalIdx,
                        "buyInSum",
                        e.target.value
                      )
                    }
                  />
                </TableCell>
                <TableCell className="text-right">
                  <input
                    type="number"
                    value={
                      player.buyOutSum === 0 ? player.inGame : player.buyOutSum
                    }
                    className={`w-full text-right bg-transparent text-foreground outline-none border rounded-lg px-2 py-1 text-sm ${
                      !isNumeric(
                        player.buyOutSum === 0
                          ? player.inGame
                          : player.buyOutSum
                      )
                        ? "border-destructive focus:border-destructive"
                        : "border-transparent focus:border-input"
                    }`}
                    onChange={(e) =>
                      handleChange(
                        player.originalIdx,
                        "buyOutSum",
                        e.target.value
                      )
                    }
                  />
                </TableCell>
                <TableCell
                  className={`text-right font-medium ${
                    player.net === 0
                      ? "text-muted-foreground"
                      : player.net > 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }`}
                >
                  <input
                    type="number"
                    value={player.net as any}
                    className="w-full text-right bg-transparent text-foreground outline-none border border-transparent focus:border-input rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(player.originalIdx, "net", e.target.value)
                    }
                  />
                </TableCell>
                <TableCell className="text-center">
                  <button
                    onClick={() => handleDelete(player.originalIdx)}
                    className="p-1 text-destructive hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                    title="Delete this player row"
                  >
                    <Trash2 size={16} />
                  </button>
                </TableCell>
              </TableRow>
            ))}
            {/* Totals Row uses shared deriveTotals */}
            <TableRow className="bg-muted">
              <TableCell colSpan={4} className="font-medium">
                Totals
              </TableCell>
              <TableCell className="text-right font-semibold">
                {formatNumber(derived.buyInTotal)}
              </TableCell>
              <TableCell className="text-right font-semibold">
                {formatNumber(derived.cashOutTotal)}
              </TableCell>
              <TableCell
                className={`text-right font-semibold ${
                  derived.net === 0
                    ? "text-muted-foreground"
                    : derived.net > 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {formatNumber(derived.net)}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && playerToDelete && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                <Trash2 className="h-6 w-6 text-red-600" />
              </div>
              <h3 className="text-lg leading-6 font-medium text-gray-900 mt-2">Delete Player Row</h3>
              <div className="mt-2 px-7 py-3">
                <p className="text-sm text-gray-500">
                  Are you sure you want to delete <strong>{playerToDelete.name}</strong>? 
                  This will remove this player from the session data.
                </p>
              </div>
              <div className="items-center px-4 py-3">
                <div className="flex space-x-2">
                  <button
                    onClick={cancelDelete}
                    className="flex-1 px-4 py-2 bg-gray-200 text-gray-900 text-base font-medium rounded-md shadow-sm hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmDelete}
                    className="flex-1 px-4 py-2 bg-red-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GameDataTable;
