import { useQuery } from "react-query";
import { fetchGameData } from "../api/game";

const useGameQuery = (gameUrl: string) => {
  return useQuery(["gameData", gameUrl], () => fetchGameData(gameUrl), {
    enabled: !!gameUrl,
  });
};

export default useGameQuery;
