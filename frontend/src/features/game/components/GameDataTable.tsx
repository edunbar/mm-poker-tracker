import React, { useMemo } from "react";
import { PlayerSummaryRow } from "../../../entities/game/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../shared/ui/table";

interface GameDataTableProps {
  playersInfos: PlayerSummaryRow[];
  setEditableData?:
    | React.Dispatch<React.SetStateAction<PlayerSummaryRow[]>>
    | (() => void);
}


function formatNumber(n: number | null | undefined) {
  return new Intl.NumberFormat().format(n ?? 0);
}

const GameDataTable: React.FC<GameDataTableProps> = ({ playersInfos = [] }) => {
  // derive totals similar to IngestDataTable's deriveTotals
  const derived = useMemo(() => {
    if (!Array.isArray(playersInfos) || playersInfos.length === 0) {
      return { buyInTotal: 0, cashOutTotal: 0, net: 0 };
    }
    const buyInTotal = playersInfos.reduce(
      (s, p) => s + (Number(p.buyIn) || 0),
      0
    );
    const cashOutTotal = playersInfos.reduce(
      (s, p) => s + (Number(p.cashOut) || 0),
      0
    );
    const net = playersInfos.reduce((s, p) => s + (Number(p.net) || 0), 0);
    const balanced = Math.round((buyInTotal - cashOutTotal) * 100) === 0;
    return { buyInTotal, cashOutTotal, net, balanced };
  }, [playersInfos]);

  if (!Array.isArray(playersInfos) || playersInfos.length === 0) {
    return <div>No player summary data available.</div>;
  }

  return (
    <div>
      <div className="overflow-auto rounded-xl border border-border bg-card">
        <Table className="table-auto w-full">
          <TableHeader className="bg-muted">
            <TableRow>
              <TableHead className="min-w-0">Player</TableHead>
              <TableHead className="text-right">Rank</TableHead>
              <TableHead className="text-right">Buy In</TableHead>
              <TableHead className="text-right">Cash Out</TableHead>
              <TableHead className="text-right">Net</TableHead>

              <TableHead className="text-right">Games</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {playersInfos.map((row, idx) => (
              <TableRow key={row.player + idx}>
                <TableCell className="px-3 py-2">{row.player}</TableCell>
                <TableCell className="px-3 py-2 text-right">
                  {row.rank}
                </TableCell>
                <TableCell className="px-3 py-2 text-right">
                  {formatNumber(row.buyIn)}
                </TableCell>
                <TableCell className="px-3 py-2 text-right">
                  {formatNumber(row.cashOut)}
                </TableCell>
                <TableCell
                  className={`px-3 py-2 text-right font-medium ${
                    row.net === 0
                      ? "text-muted-foreground"
                      : row.net > 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }`}
                >
                  {formatNumber(row.net)}
                </TableCell>

                <TableCell className="px-3 py-2 text-right">
                  {row.gamesPlayed}
                </TableCell>
              </TableRow>
            ))}

            <TableRow className="bg-muted">
              <TableCell colSpan={2} className="font-medium">
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
              <TableCell colSpan={8} />
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default GameDataTable;
