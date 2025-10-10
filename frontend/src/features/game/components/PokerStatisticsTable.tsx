import React, { useMemo } from "react";
import { Badge } from "../../../shared/ui/badge";
import { EnhancedDataTable, createColumn } from "../../../shared/ui/enhanced-data-table";
import { HelpTooltip } from "../../../shared/ui/help-tooltip";
import { PlayerStatistic } from "../api/getPokerStatistics";

interface PokerStatisticsTableProps {
  players: PlayerStatistic[];
  className?: string;
}

function formatPercentage(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "0.0%";
  }
  return `${Number(value).toFixed(1)}%`;
}

function getPlayStyleColor(playStyle: string): string {
  // Map of new fun style names to colors
  const colorMap: { [key: string]: string } = {
    // Special cases
    'Calling Station': 'bg-red-100 text-red-800 hover:bg-red-200',
    'Maniac': 'bg-purple-100 text-purple-800 hover:bg-purple-200',
    'ATM': 'bg-red-100 text-red-800 hover:bg-red-200',
    'Super Nit': 'bg-gray-100 text-gray-800 hover:bg-gray-200',
    'Nit': 'bg-gray-100 text-gray-800 hover:bg-gray-200',

    // Very loose styles
    'Splashy Aggressive': 'bg-blue-100 text-blue-800 hover:bg-blue-200',
    'Splashy Balanced': 'bg-cyan-100 text-cyan-800 hover:bg-cyan-200',

    // Loose styles
    'LAG Monster': 'bg-red-100 text-red-800 hover:bg-red-200',
    'Action Player': 'bg-blue-100 text-blue-800 hover:bg-blue-200',
    'Loose Cannon': 'bg-orange-100 text-orange-800 hover:bg-orange-200',
    'Passive Fish': 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',

    // Standard styles
    'Aggressive Regular': 'bg-green-100 text-green-800 hover:bg-green-200',
    'Active Player': 'bg-green-100 text-green-800 hover:bg-green-200',
    'Passive Regular': 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',

    // Tight styles
    'TAG Crusher': 'bg-green-100 text-green-800 hover:bg-green-200',
    'Selective Aggressive': 'bg-green-100 text-green-800 hover:bg-green-200',
    'Cautious Player': 'bg-slate-100 text-slate-800 hover:bg-slate-200',
    'Rock': 'bg-gray-100 text-gray-800 hover:bg-gray-200',

    // Legacy support
    'TAG': 'bg-green-100 text-green-800 hover:bg-green-200',
    'LAG': 'bg-blue-100 text-blue-800 hover:bg-blue-200',
    'TP': 'bg-gray-100 text-gray-800 hover:bg-gray-200',
    'LP': 'bg-red-100 text-red-800 hover:bg-red-200',
  };

  return colorMap[playStyle] || 'bg-slate-100 text-slate-800 hover:bg-slate-200';
}

function getPlayStyleDescription(playStyle: string): string {
  // Map of new fun style names to descriptions
  const descriptionMap: { [key: string]: string } = {
    // Special cases
    'Calling Station': 'Plays everything, never raises - the ATM of poker',
    'Maniac': 'Maximum chaos - plays and raises with almost everything',
    'ATM': 'Gives money away by playing too many weak hands',
    'Super Nit': 'Barely plays at all - waiting for pocket aces',
    'Nit': 'Extremely tight even for this game',

    // Very loose styles
    'Splashy Aggressive': 'Sees lots of flops and plays them aggressively',
    'Splashy Balanced': 'Action player with decent balance',

    // Loose styles
    'LAG Monster': 'Loose and extremely aggressive - dangerous opponent',
    'Action Player': 'Creates lots of action and plays aggressively',
    'Loose Cannon': 'Unpredictable loose player',
    'Passive Fish': 'Plays many hands but lacks aggression',

    // Standard styles
    'Aggressive Regular': 'Solid aggressive player for this game type',
    'Active Player': 'Well-balanced and active style',
    'Passive Regular': 'Reasonable range but lacks aggression',

    // Tight styles
    'TAG Crusher': 'Tight-aggressive crusher - premium hands only',
    'Selective Aggressive': 'Selective but aggressive when involved',
    'Cautious Player': 'Plays it safe - solid but predictable',
    'Rock': 'Extremely passive - calls more than raises',

    // Legacy support
    'TAG': 'Tight-Aggressive: Plays few hands but plays them aggressively',
    'LAG': 'Loose-Aggressive: Plays many hands aggressively',
    'TP': 'Tight-Passive (Nit): Plays few hands and rarely bets/raises',
    'LP': 'Loose-Passive (Fish): Plays many hands but calls more than bets/raises',
  };

  return descriptionMap[playStyle] || 'Playing style could not be determined from available data';
}

function getPlayStyleAbbreviation(playStyle: string): string {
  // Map of style names to mobile-friendly abbreviations
  const abbreviationMap: { [key: string]: string } = {
    // Special cases
    'Calling Station': 'Call Stn',
    'Maniac': 'Maniac',
    'ATM': 'ATM',
    'Super Nit': 'S. Nit',
    'Nit': 'Nit',

    // Very loose styles
    'Splashy Aggressive': 'Splashy',
    'Splashy Balanced': 'Splashy',

    // Loose styles
    'LAG Monster': 'LAG',
    'Action Player': 'Action',
    'Loose Cannon': 'Loose',
    'Passive Fish': 'Pass Fish',

    // Standard styles
    'Aggressive Regular': 'Agg Reg',
    'Active Player': 'Active',
    'Passive Regular': 'Passive',

    // Tight styles
    'TAG Crusher': 'TAG',
    'Selective Aggressive': 'Sel Agg',
    'Cautious Player': 'Cautious',
    'Rock': 'Rock',

    // Legacy support
    'TAG': 'TAG',
    'LAG': 'LAG',
    'TP': 'TP',
    'LP': 'LP',
  };

  return abbreviationMap[playStyle] || playStyle;
}


const PokerStatisticsTable: React.FC<PokerStatisticsTableProps> = ({
  players = [],
  className
}) => {
  // Custom sorting state - start unsorted to match backend's initial state
  const [sortConfig, setSortConfig] = React.useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

  const handleSort = (columnId: string) => {
    setSortConfig(prevConfig => {
      // If clicking the same column that's already sorted
      if (prevConfig && prevConfig.key === columnId) {
        // Toggle: desc -> asc -> null
        if (prevConfig.direction === 'desc') {
          return { key: columnId, direction: 'asc' };
        }
        return null; // Remove sorting
      }
      // New column: start with desc
      return { key: columnId, direction: 'desc' };
    });
  };

  const sortedData = React.useMemo(() => {
    if (!sortConfig) return players;

    return [...players].sort((a, b) => {
      const aValue = (a as unknown as Record<string, unknown>)[sortConfig.key];
      const bValue = (b as unknown as Record<string, unknown>)[sortConfig.key];

      // Handle null/undefined values - push them to the end
      if (aValue === null || aValue === undefined) {
        if (bValue === null || bValue === undefined) return 0;
        return 1;
      }
      if (bValue === null || bValue === undefined) return -1;

      // Numeric comparison
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        const diff = aValue - bValue;
        return sortConfig.direction === 'asc' ? diff : -diff;
      }

      // String comparison
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();
      if (aStr < bStr) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aStr > bStr) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [players, sortConfig]);

  const columns = useMemo(() => [
    createColumn('playerName', 'Player', 'playerName', {
      sortable: true,
      className: 'font-semibold text-left',
      width: 'auto',
    }),
    createColumn('handsPlayed', 'Hands', (row: PlayerStatistic) => (
      <span className="font-medium">{row.handsPlayed}</span>
    ), {
      sortable: true,
      align: 'left' as const,
      className: 'font-medium text-left',
      width: 'auto',
    }),
    createColumn('vpip', 'VPIP', (row: PlayerStatistic) => (
      <span className="font-sans font-medium">
        {formatPercentage(row.vpip)}
      </span>
    ), {
      sortable: true,
      align: 'left' as const,
      className: 'text-left',
      width: 'auto',
    }),
    createColumn('pfr', 'PFR', (row: PlayerStatistic) => (
      <span className="font-sans font-medium">
        {formatPercentage(row.pfr)}
      </span>
    ), {
      sortable: true,
      align: 'left' as const,
      className: 'text-left',
      width: 'auto',
    }),
    createColumn('aggressionFrequency', 'AF', (row: PlayerStatistic) => (
      <span className="font-sans font-medium">
        {formatPercentage(row.aggressionFrequency)}
      </span>
    ), {
      sortable: true,
      align: 'left' as const,
      className: 'text-left hidden md:table-cell',
      width: 'auto',
    }),
    createColumn('playStyle', 'Style', (row: PlayerStatistic) => (
      <div className="flex items-center gap-2">
        <Badge
          variant="secondary"
          className={`${row.styleColor || getPlayStyleColor(row.playStyle)} font-medium whitespace-nowrap text-xs sm:text-sm px-2 py-0.5 sm:px-2.5 sm:py-1`}
        >
          <span className="md:hidden">{getPlayStyleAbbreviation(row.playStyle)}</span>
          <span className="hidden md:inline">{row.playStyle}</span>
        </Badge>
        <span className="hidden md:inline">
          <HelpTooltip
            content={row.styleDescription || getPlayStyleDescription(row.playStyle)}
            position="below"
          />
        </span>
      </div>
    ), {
      sortable: true,
      align: 'left' as const,
      className: 'text-left',
      width: 'auto',
    }),
    createColumn('streetBreakdown', 'Street AF', (row: PlayerStatistic) => (
      <div className="text-sm space-y-1 bg-muted/30 rounded px-3 py-2 inline-block">
        <div className="flex justify-between items-center gap-3">
          <span className="text-muted-foreground font-medium">F:</span>
          <span className="font-sans font-medium">{formatPercentage(row.flopAF)}</span>
        </div>
        <div className="flex justify-between items-center gap-3">
          <span className="text-muted-foreground font-medium">T:</span>
          <span className="font-sans font-medium">{formatPercentage(row.turnAF)}</span>
        </div>
        <div className="flex justify-between items-center gap-3">
          <span className="text-muted-foreground font-medium">R:</span>
          <span className="font-sans font-medium">{formatPercentage(row.riverAF)}</span>
        </div>
      </div>
    ), {
      sortable: false,
      align: 'left' as const,
      className: 'text-left hidden lg:table-cell',
      width: 'auto',
    }),
  ], []);

  if (!Array.isArray(players) || players.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No poker statistics available. Statistics are calculated from hand-level data after sessions are processed.
      </div>
    );
  }

  return (
    <div className={className}>
      <EnhancedDataTable
        data={sortedData}
        columns={columns}
        {...(sortConfig ? { sortConfig } : {})}
        onSort={handleSort}
        className="rounded-xl"
        variant="default"
        emptyState={
          <div className="text-center py-8 text-muted-foreground">
            No poker statistics available.
          </div>
        }
      />
    </div>
  );
};

export default PokerStatisticsTable;