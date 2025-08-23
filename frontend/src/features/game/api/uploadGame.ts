export {};
import { useMutation } from "react-query";
import axios from "axios";

export const uploadGameToSheets = async (playersInfos: any[]) => {
  const response = await axios.post(
    "http://localhost:8000/api/games/upload_to_sheets",
    { playersInfos }
  );
  return response.data;
};

export function useUploadGame() {
  return useMutation(uploadGameToSheets);
}
