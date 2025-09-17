import axios from "axios";
import { useQuery } from "react-query";
import { API_BASE_URL } from "../../../config/api";

interface PlayerAnalytics {
  player_name: string;
  total_games: number;
  total_wins: number;
  total_losses: number;
  current_losing_streak: number;
  longest_losing_streak: number;
  current_winning_streak: number;
  longest_winning_streak: number;
  never_profitable: boolean;
  total_net: number;
  total_buy_in: number;
  longest_winning_streak_net: number;
  longest_losing_streak_net: number;
}

interface AnalyticsResponse {
  analytics: Record<string, PlayerAnalytics>;
}

export const fetchPlayerAnalytics = async (publicCode: string): Promise<AnalyticsResponse> => {
  const response = await axios.get(
    `${API_BASE_URL}/api/games/${publicCode}/analytics`
  );
  return response.data;
};

export function usePlayerAnalytics(publicCode: string) {
  return useQuery(
    ["playerAnalytics", publicCode],
    () => fetchPlayerAnalytics(publicCode),
    {
      enabled: !!publicCode,
      refetchOnWindowFocus: false,
      staleTime: 10 * 1000, // 10 seconds - temporarily reduced
      cacheTime: 30 * 1000, // 30 seconds - temporarily reduced
      retry: 2, // Retry failed requests twice
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
    }
  );
}