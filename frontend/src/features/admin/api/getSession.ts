import axios from "axios";
import { useQuery } from "react-query";

export const fetchGameData = async (gameUrl: string) => {
  const response = await axios.get(
    "http://localhost:8000/api/games/get_transactions",
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
