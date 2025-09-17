import axios from "axios";
import { useQuery } from "react-query";
import { API_BASE_URL } from "../../config/api";

interface GameInfo {
  title?: string;
  public_code: string;
}

export const fetchGameInfo = async (publicCode: string): Promise<GameInfo> => {
  // Reuse the existing summary endpoint which already returns the game title
  const response = await axios.get(
    `${API_BASE_URL}/api/games/${publicCode}/summary`
  );
  return response.data;
};

export function useGameTitle(publicCode: string) {
  const query = useQuery(
    ["gameTitle", publicCode],
    () => fetchGameInfo(publicCode),
    {
      enabled: !!publicCode,
      refetchOnWindowFocus: false,
    }
  );

  const title = query.data?.title?.trim() ? query.data.title : publicCode;
  
  return {
    ...query,
    title
  };
}