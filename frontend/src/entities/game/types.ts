export interface PlayerInfo {
  id: string;
  names: string[];
  buyInSum: number;
  buyOutSum: number;
  inGame: number;
  net: number;
  validated_name?: string;
}

export interface PlayerSummaryRow {
  player: string;
  rank: number;
  buyIn: number;
  cashOut: number;
  net: number;
  gamesPlayed: number;
}

export interface PlayerSummaryApiResponse {
  game: string;
  title?: string | null;
  rows: PlayerSummaryRow[];
}
