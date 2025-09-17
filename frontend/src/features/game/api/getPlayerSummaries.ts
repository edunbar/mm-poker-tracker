import axios from "axios";
import { useQuery } from "react-query";
import { API_BASE_URL } from "../../../config/api";

export const fetchPlayerSummaries = async (publicCode: string) => {
  const response = await axios.get(
    `${API_BASE_URL}/api/games/${publicCode}/summary`
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
