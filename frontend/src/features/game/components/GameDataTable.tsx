import React, { useMemo } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../shared/ui/table";
import { PlayerInfo } from "../../../entities/game/types";
import { deriveTotals } from "../lib/deriveTotals";
import { isNumeric } from "../lib/validation";

function formatNumber(n: number) {
  return new Intl.NumberFormat().format(n || 0);
}

interface GameDataTableProps {
  playersInfos: PlayerInfo[];
  setEditableData: React.Dispatch<React.SetStateAction<PlayerInfo[]>>;
}

const GameDataTable: React.FC<GameDataTableProps> = ({
  playersInfos,
  setEditableData,
}) => {
  // keep a stable mapping back to original index so edits update correct item
  const sortedPlayers = playersInfos
    .map((player, originalIdx) => ({ ...player, originalIdx }))
    .sort((a, b) => b.net - a.net);

  // Use shared deriveTotals/validation utilities
  const derived = useMemo(() => deriveTotals(playersInfos), [playersInfos]);

  const balanced = derived.balanced;

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

  if (!Array.isArray(playersInfos) || playersInfos.length === 0) {
    return <div>No player data available.</div>;
  }

  return (
    <div>
      {/* Editable Table */}
      <div className="overflow-auto rounded-xl border">
        <Table>
          <TableHeader className="bg-gray-50">
            <TableRow>
              <TableHead className="min-w-[120px]">ID</TableHead>
              <TableHead className="min-w-[170px]">Name</TableHead>
              <TableHead className="min-w-[220px]">IGN</TableHead>
              <TableHead className="w-[140px] text-right">Buy In</TableHead>
              <TableHead className="w-[140px] text-right">Cash Out</TableHead>
              <TableHead className="w-[120px] text-right">Net</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedPlayers.map((player) => (
              <TableRow
                key={player.id || player.originalIdx}
                className="hover:bg-gray-50"
              >
                <TableCell>
                  <input
                    type="text"
                    value={player.id}
                    className="w-full bg-transparent outline-none border border-transparent focus:border-gray-300 rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(player.originalIdx, "id", e.target.value)
                    }
                  />
                </TableCell>
                <TableCell>
                  <input
                    type="text"
                    value={player.validated_name || ""}
                    className="w-full bg-transparent outline-none border border-transparent focus:border-gray-300 rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(
                        player.originalIdx,
                        "validated_name",
                        e.target.value
                      )
                    }
                  />
                </TableCell>
                <TableCell>
                  <input
                    type="text"
                    value={
                      Array.isArray(player.names)
                        ? player.names.join(", ")
                        : player.names
                    }
                    className="w-full bg-transparent outline-none border border-transparent focus:border-gray-300 rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(player.originalIdx, "names", e.target.value)
                    }
                  />
                </TableCell>
                <TableCell className="text-right">
                  <input
                    type="number"
                    value={player.buyInSum as any}
                    className={`w-full text-right bg-transparent outline-none border rounded-lg px-2 py-1 text-sm ${
                      !isNumeric(player.buyInSum)
                        ? "border-red-300 focus:border-red-400"
                        : "border-transparent focus:border-gray-300"
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
                    className={`w-full text-right bg-transparent outline-none border rounded-lg px-2 py-1 text-sm ${
                      !isNumeric(
                        player.buyOutSum === 0
                          ? player.inGame
                          : player.buyOutSum
                      )
                        ? "border-red-300 focus:border-red-400"
                        : "border-transparent focus:border-gray-300"
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
                      ? "text-gray-700"
                      : player.net > 0
                      ? "text-emerald-600"
                      : "text-red-600"
                  }`}
                >
                  <input
                    type="number"
                    value={player.net as any}
                    className="w-full text-right bg-transparent outline-none border border-transparent focus:border-gray-300 rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(player.originalIdx, "net", e.target.value)
                    }
                  />
                </TableCell>
              </TableRow>
            ))}
            {/* Totals Row uses shared deriveTotals */}
            <TableRow className="bg-gray-50">
              <TableCell colSpan={3} className="font-medium">
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
                    ? "text-gray-700"
                    : derived.net > 0
                    ? "text-emerald-700"
                    : "text-red-700"
                }`}
              >
                {formatNumber(derived.net)}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default GameDataTable;
