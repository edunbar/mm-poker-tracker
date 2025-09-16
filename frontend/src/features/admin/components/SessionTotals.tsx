interface PlayerInfo {
  buyInSum: number;
  buyOutSum: number;
  inGame: number;
}

interface GameTotalsProps {
  playersInfos: PlayerInfo[];
}

const GameTotals: React.FC<GameTotalsProps> = ({ playersInfos }) => {
  // Calculate totals
  const buyInTotal = playersInfos.reduce(
    (sum, p) => sum + Number(p.buyInSum || 0),
    0
  );
  const buyOutTotal = playersInfos.reduce(
    (sum, p) => sum + Number(p.buyOutSum || 0),
    0
  );
  const inGameTotal = playersInfos.reduce(
    (sum, p) => sum + Number(p.inGame || 0),
    0
  );

  const cashOutTotal = buyOutTotal + inGameTotal;
  const netTotal = buyInTotal - cashOutTotal;
  const isBalanced = netTotal === 0;

  return (
    <div style={{ marginBottom: "1rem" }}>
      <div>
        <strong>Buy In Total: </strong>
        <span>{buyInTotal}</span>
      </div>
      <div>
        <strong>Cash Out Total: </strong>
        <span>{cashOutTotal}</span>
      </div>
      <div>
        <strong>Net: </strong>
        <span style={{ color: isBalanced ? "green" : "red" }}>{netTotal}</span>
      </div>
      {!isBalanced && (
        <div style={{ color: "red", fontWeight: "bold" }}>
          Error: Buy In Total and Cash Out Total must net to 0!
        </div>
      )}
    </div>
  );
};

export default GameTotals;
