import { useQuery } from "react-query";
import { fetchGameData } from "./game";

const useGameQuery = (gameUrl: string) => {
  return useQuery(["gameData", gameUrl], () => fetchGameData(gameUrl), {
    enabled: !!gameUrl,
    refetchOnWindowFocus: false,
  });
};

export default useGameQuery;
