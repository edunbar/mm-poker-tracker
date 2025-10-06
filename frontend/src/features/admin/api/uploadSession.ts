import { useMutation } from "react-query";
import { apiClient } from "../../../api/client";

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
  admin_code?: string;
  sessionId: string;
  game_data: unknown;
  date?: string;
  gameNumber?: number;
  ledger_csv_content?: string;
}) => {
  const headers: Record<string, string> = {};

  // Only send X-Admin-Code if provided (for non-authenticated users)
  if (admin_code) {
    headers['X-Admin-Code'] = admin_code;
  }

  const response = await apiClient.post(
    '/api/games/upload',
    {
      public_code,
      sessionId,
      game_data,
      date,
      gameNumber,
      ledger_csv_content,
    },
    {
      headers,
    }
  );
  return response.data;
};

export function useUploadGame() {
  return useMutation(uploadGameDualWrite);
}
