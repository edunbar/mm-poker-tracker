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
    <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
      <div className="border-b border-border p-4">
        <h3 className="text-lg font-semibold text-foreground">Session Summary</h3>
      </div>
      <div className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-sm font-medium text-muted-foreground mb-1">Buy In Total</div>
            <div className="text-2xl font-bold text-foreground">
              {formatNumber(buyInTotal)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm font-medium text-muted-foreground mb-1">Cash Out Total</div>
            <div className="text-2xl font-bold text-foreground">
              {formatNumber(cashOutTotal)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm font-medium text-muted-foreground mb-1">Net</div>
            <div className={`text-2xl font-bold ${
              net === 0 ? 'text-foreground' : net > 0 ? 'text-success' : 'text-destructive'
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
