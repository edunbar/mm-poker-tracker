import React, { useMemo } from "react";
import { PlayerSummaryRow } from "../../../entities/game/types";
import { EnhancedDataTable, createColumn, useTableState } from "../../../shared/ui/enhanced-data-table";

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
  // Use table state hook for sorting
  const { sortConfig, sortedData, handleSort } = useTableState(playersInfos, 'rank', 'asc');
  // derive totals similar to IngestDataTable's deriveTotals
  const derived = useMemo(() => {
    if (!Array.isArray(sortedData) || sortedData.length === 0) {
      return { buyInTotal: 0, cashOutTotal: 0, net: 0 };
    }
    const buyInTotal = sortedData.reduce(
      (s, p) => s + (Number(p.buyIn) || 0),
      0
    );
    const cashOutTotal = sortedData.reduce(
      (s, p) => s + (Number(p.cashOut) || 0),
      0
    );
    const net = sortedData.reduce((s, p) => s + (Number(p.net) || 0), 0);
    const balanced = Math.round((buyInTotal - cashOutTotal) * 100) === 0;
    return { buyInTotal, cashOutTotal, net, balanced };
  }, [sortedData]);

  const columns = useMemo(() => [
    createColumn('player', 'Player', 'player', {
      sortable: true,
      className: 'min-w-0'
    }),
    createColumn('rank', 'Rank', 'rank', {
      sortable: true,
      className: 'hidden md:table-cell'
    }),
    createColumn('buyIn', 'Buy In', (row: PlayerSummaryRow) => formatNumber(row.buyIn), {
      sortable: true
    }),
    createColumn('cashOut', 'Cash Out', (row: PlayerSummaryRow) => formatNumber(row.cashOut), {
      sortable: true
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
      sortable: true
    }),
    createColumn('gamesPlayed', 'Games', 'gamesPlayed', {
      sortable: true,
      className: 'hidden md:table-cell'
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
    return [...sortedData, totalsRow];
  }, [sortedData, derived]);

  if (!Array.isArray(playersInfos) || playersInfos.length === 0) {
    return <div>No player summary data available.</div>;
  }

  return (
    <EnhancedDataTable
      data={dataWithTotals}
      columns={columns}
      {...(sortConfig && { sortConfig })}
      onSort={handleSort}
      className="rounded-xl"
      variant="default"
      emptyState={<div>No player summary data available.</div>}
    />
  );
};

export default GameDataTable;