import { PlayerInfo } from "@entities/game/types";

export function deriveTotals(rows: PlayerInfo[]) {
  const buyInTotal = rows.reduce((s, r) => s + Number(r.buyInSum || 0), 0);
  const cashOutTotal = rows.reduce(
    (s, r) => s + Number(r.buyOutSum || 0) + Number(r.inGame || 0),
    0
  );
  const net = cashOutTotal - buyInTotal;
  const hasInvalid = rows.some(
    (r) =>
      Number.isNaN(Number(r.buyInSum)) ||
      Number.isNaN(Number(r.buyOutSum)) ||
      Number.isNaN(Number(r.inGame))
  );
  return {
    buyInTotal,
    cashOutTotal,
    net,
    hasInvalid,
    balanced: net === 0 && !hasInvalid,
  };
}
