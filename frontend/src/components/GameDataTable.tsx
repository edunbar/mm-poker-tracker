import React, { useMemo } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";

function formatNumber(n: number) {
  return new Intl.NumberFormat().format(n || 0);
}
function isNumeric(value: any) {
  return value !== null && value !== "" && !Number.isNaN(Number(value));
}

export interface PlayerInfo {
  id: string;
  names: string;
  buyInSum: number;
  buyOutSum: number;
  inGame: number;
  net: number;
  validated_name?: string;
}

interface GameDataTableProps {
  playersInfos: PlayerInfo[];
  setEditableData: React.Dispatch<React.SetStateAction<PlayerInfo[]>>;
}

const GameDataTable: React.FC<GameDataTableProps> = ({
  playersInfos,
  setEditableData,
}) => {
  // Sort players by net, biggest to smallest
  const sortedPlayers = playersInfos
    .map((player, originalIdx) => ({ ...player, originalIdx }))
    .sort((a, b) => b.net - a.net);

  // Derived totals and validation
  const derived = useMemo(() => {
    const buyInTotal = sortedPlayers.reduce(
      (sum, p) => sum + Number(p.buyInSum || 0),
      0
    );
    const cashOutTotal = sortedPlayers.reduce(
      (sum, p) => sum + Number(p.buyOutSum === 0 ? p.inGame : p.buyOutSum || 0),
      0
    );
    const net = cashOutTotal - buyInTotal;
    const hasInvalid = sortedPlayers.some(
      (r) =>
        !isNumeric(r.buyInSum) ||
        !isNumeric(r.buyOutSum === 0 ? r.inGame : r.buyOutSum)
    );
    return { buyInTotal, cashOutTotal, net, hasInvalid };
  }, [sortedPlayers]);

  const balanced = derived.net === 0 && !derived.hasInvalid;

  const handleChange = (
    index: number,
    field: keyof PlayerInfo,
    value: string | number | boolean
  ) => {
    const updated = [...playersInfos];
    if (field === "buyInSum" || field === "buyOutSum") {
      updated[index][field] = Number(value);
      updated[index].net =
        (updated[index].buyOutSum === 0
          ? updated[index].inGame
          : updated[index].buyOutSum) - updated[index].buyInSum;
    } else if (field === "net") {
      updated[index][field] = Number(value);
    } else if (field === "id") {
      updated[index][field] = value as string;
    } else if (field === "names") {
      updated[index][field] = (value as string)
        .split(",")
        .map((n) => n.trim())
        .join(",");
    } else if (field === "validated_name") {
      updated[index][field] = value as string;
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
            {sortedPlayers.map((player, idx) => (
              <TableRow key={player.id || idx} className="hover:bg-gray-50">
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
                    value={player.buyInSum}
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
                    value={player.net}
                    className="w-full text-right bg-transparent outline-none border border-transparent focus:border-gray-300 rounded-lg px-2 py-1 text-sm"
                    onChange={(e) =>
                      handleChange(player.originalIdx, "net", e.target.value)
                    }
                  />
                </TableCell>
              </TableRow>
            ))}
            {/* Totals Row */}
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

export default GameDataTable;
