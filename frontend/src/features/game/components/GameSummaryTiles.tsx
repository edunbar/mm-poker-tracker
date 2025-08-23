import React from "react";

function formatNumber(n: number) {
  return new Intl.NumberFormat().format(n || 0);
}

interface GameSummaryTilesProps {
  buyInTotal: number;
  cashOutTotal: number;
  net: number;
}

const GameSummaryTiles: React.FC<GameSummaryTilesProps> = ({
  buyInTotal,
  cashOutTotal,
  net,
}) => {
  const accent = net === 0 ? "ok" : net > 0 ? "pos" : "neg";
  const accentMap: Record<string, string> = {
    ok: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    pos: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    neg: "bg-red-50 text-red-700 ring-red-200",
    base: "bg-white text-gray-900 ring-gray-200",
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
      <div
        className={`shadow-sm ring-1 ${accentMap.base} border-none p-4 rounded-lg`}
      >
        <div className="text-sm text-gray-500 mb-1">Buy In Total</div>
        <div className="text-2xl font-semibold tracking-tight">
          {formatNumber(buyInTotal)}
        </div>
      </div>
      <div
        className={`shadow-sm ring-1 ${accentMap.base} border-none p-4 rounded-lg`}
      >
        <div className="text-sm text-gray-500 mb-1">Cash Out Total</div>
        <div className="text-2xl font-semibold tracking-tight">
          {formatNumber(cashOutTotal)}
        </div>
      </div>
      <div
        className={`shadow-sm ring-1 ${accentMap[accent]} border-none p-4 rounded-lg`}
      >
        <div className="text-sm text-gray-500 mb-1">Net</div>
        <div className="text-2xl font-semibold tracking-tight">
          {formatNumber(net)}
        </div>
      </div>
    </div>
  );
};

export default GameSummaryTiles;
