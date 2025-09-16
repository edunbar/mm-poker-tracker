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

  return (
    <div className="bg-white rounded-lg border shadow-sm">
      <div className="border-b p-4">
        <h3 className="text-lg font-semibold">Session Summary</h3>
      </div>
      <div className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-sm font-medium text-gray-600 mb-1">Buy In Total</div>
            <div className="text-2xl font-bold text-gray-900">
              {formatNumber(buyInTotal)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm font-medium text-gray-600 mb-1">Cash Out Total</div>
            <div className="text-2xl font-bold text-gray-900">
              {formatNumber(cashOutTotal)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm font-medium text-gray-600 mb-1">Net</div>
            <div className={`text-2xl font-bold ${
              net === 0 ? 'text-gray-900' : net > 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {net > 0 ? '+' : ''}{formatNumber(net)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GameSummaryTiles;
