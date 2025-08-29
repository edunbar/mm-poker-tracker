import { useQuery } from "react-query";
import { fetchGameData } from "./session";

const useGameQuery = (gameUrl: string) => {
  return useQuery(["gameData", gameUrl], () => fetchGameData(gameUrl), {
    enabled: !!gameUrl,
    refetchOnWindowFocus: false,
  });
};

export default useGameQuery;
