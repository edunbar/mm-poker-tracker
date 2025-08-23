export interface PlayerInfo {
  id: string;
  names: string[];
  buyInSum: number;
  buyOutSum: number;
  inGame: number;
  net: number;
  validated_name?: string;
}
