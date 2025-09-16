import axios from "axios";
import { useQuery } from "react-query";

export const fetchPlayerSummaries = async (publicCode: string) => {
  const response = await axios.get(
    `http://localhost:8000/api/games/${publicCode}/summary`
  );
  return response.data;
};

export function usePlayerSummaries(publicCode: string) {
  return useQuery(
    ["playerSummaries", publicCode],
    () => fetchPlayerSummaries(publicCode),
    {
      enabled: !!publicCode,
      refetchOnWindowFocus: false,
    }
  );
}
