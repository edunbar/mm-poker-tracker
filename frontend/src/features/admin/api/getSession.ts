import axios from "axios";
import { useQuery } from "react-query";
import { API_BASE_URL } from "../../../config/api";

export const fetchGameData = async (gameUrl: string) => {
  const response = await axios.get(
    `${API_BASE_URL}/api/games/get_transactions`,
    { params: { url: gameUrl } }
  );
  return response.data;
};

export function useGetGame(gameUrl: string) {
  return useQuery(["gameData", gameUrl], () => fetchGameData(gameUrl), {
    enabled: !!gameUrl,
    refetchOnWindowFocus: false,
  });
}