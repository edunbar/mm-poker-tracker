import axios from "axios";
import { useQuery } from "react-query";
import { API_BASE_URL } from "../../../config/api";

interface SessionExtreme {
  player_name: string;
  game_number: number;
  session_name: string;
  external_id: string;
  net: number;
  buy_in_sum: number;
  cash_out_sum: number;
  in_game: number;
}

interface SessionExtremesResponse {
  best_sessions: SessionExtreme[];
  worst_sessions: SessionExtreme[];
}

export const fetchSessionExtremes = async (publicCode: string): Promise<SessionExtremesResponse> => {
  const response = await axios.get(
    `${API_BASE_URL}/api/games/${publicCode}/session-extremes`
  );
  return response.data;
};

export function useSessionExtremes(publicCode: string) {
  return useQuery(
    ["sessionExtremes", publicCode],
    () => fetchSessionExtremes(publicCode),
    {
      enabled: !!publicCode,
      refetchOnWindowFocus: false,
      staleTime: 10 * 1000, // 10 seconds - data is considered fresh (temporarily reduced)
      cacheTime: 30 * 1000, // 30 seconds - keep in cache (temporarily reduced)
      retry: 2, // Retry failed requests twice
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
    }
  );
}