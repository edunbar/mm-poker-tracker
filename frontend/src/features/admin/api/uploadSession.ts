import { useMutation } from "react-query";
import axios from "axios";

export const uploadGameDualWrite = async ({
  public_code,
  admin_code,
  sessionId,
  game_data,
  date,
}: {
  public_code: string;
  admin_code: string;
  sessionId: string;
  game_data: any;
  date?: string;
}) => {
  const response = await axios.post(
    "http://localhost:8000/api/games/upload",
    {
      public_code,
      sessionId,
      game_data,
      date,
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
