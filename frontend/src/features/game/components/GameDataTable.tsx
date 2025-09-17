import React, { useMemo } from "react";
import { PlayerSummaryRow } from "../../../entities/game/types";
import { EnhancedDataTable, createColumn } from "../../../shared/ui/enhanced-data-table";

interface GameDataTableProps {
  playersInfos: PlayerSummaryRow[];
  setEditableData?:
    | React.Dispatch<React.SetStateAction<PlayerSummaryRow[]>>
    | (() => void);
}

function formatNumber(n: number | null | undefined) {
  // Handle negative zero by normalizing very small values to 0
  const value = n ?? 0;
  const normalized = Math.abs(value) < 0.005 ? 0 : value;
  return new Intl.NumberFormat().format(normalized);
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

  const columns = useMemo(() => [
    createColumn('player', 'Player', 'player', {
      sortable: true,
      className: 'min-w-0'
    }),
    createColumn('rank', 'Rank', 'rank', {
      sortable: true,
      align: 'right' as const
    }),
    createColumn('buyIn', 'Buy In', (row: PlayerSummaryRow) => formatNumber(row.buyIn), {
      sortable: true,
      align: 'right' as const
    }),
    createColumn('cashOut', 'Cash Out', (row: PlayerSummaryRow) => formatNumber(row.cashOut), {
      sortable: true,
      align: 'right' as const
    }),
    createColumn('net', 'Net', (row: PlayerSummaryRow) => (
      <span className={`font-medium ${
        Math.abs(row.net) < 0.005
          ? "text-muted-foreground"
          : row.net > 0.005
          ? "text-success"
          : "text-destructive"
      }`}>
        {formatNumber(row.net)}
      </span>
    ), {
      sortable: true,
      align: 'right' as const
    }),
    createColumn('gamesPlayed', 'Games', 'gamesPlayed', {
      sortable: true,
      align: 'right' as const
    }),
  ], []);

  // Create data with totals row
  const dataWithTotals = useMemo(() => {
    const totalsRow: PlayerSummaryRow = {
      player: 'Totals',
      rank: 0,
      buyIn: derived.buyInTotal,
      cashOut: derived.cashOutTotal,
      net: derived.net,
      gamesPlayed: 0,
    };
    return [...playersInfos, totalsRow];
  }, [playersInfos, derived]);

  if (!Array.isArray(playersInfos) || playersInfos.length === 0) {
    return <div>No player summary data available.</div>;
  }

  return (
    <EnhancedDataTable
      data={dataWithTotals}
      columns={columns}
      className="rounded-xl"
      variant="default"
      emptyState={<div>No player summary data available.</div>}
    />
  );
};

export default GameDataTable;