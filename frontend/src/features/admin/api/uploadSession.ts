import axios from "axios";
import { useMutation } from "react-query";
import { API_BASE_URL } from "../../../config/api";

export const uploadGameDualWrite = async ({
  public_code,
  admin_code,
  sessionId,
  game_data,
  date,
  gameNumber,
  ledger_csv_content,
}: {
  public_code: string;
  admin_code: string;
  sessionId: string;
  game_data: unknown;
  date?: string;
  gameNumber?: number;
  ledger_csv_content?: string;
}) => {
  const response = await axios.post(
    `${API_BASE_URL}/api/games/upload`,
    {
      public_code,
      sessionId,
      game_data,
      date,
      gameNumber,
      ledger_csv_content,
    },
    {
      headers: {
        "X-Admin-Code": admin_code,
      },
    }
  );
  return response.data;
};

export function useUploadGame() {
  return useMutation(uploadGameDualWrite);
}
