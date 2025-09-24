import axios from "axios";
import { useQuery } from "react-query";
import { API_BASE_URL } from "../../../config/api";

export interface HandReplay {
  hand_number: number;
  pot_size: number;
  winner_name: string;
  board_cards: string;
  action_log: string[];
}

export interface SessionHandAnalytics {
  session_id: string;
  session_number: number;
  date: string;
  total_actions: number;
  duration_hours: number;
  total_hands: number;
  hands_per_hour: number;
  active_players: number;
  top_winners: Array<{
    player_id: string;
    player_name: string;
    hands_won: number;
    win_percentage: number;
    biggest_pot: number;
  }>;
  top_10_hands: HandReplay[];
}

export interface HandAnalyticsResponse {
  sessions: SessionHandAnalytics[];
  total_sessions_with_hand_data: number;
  total_sessions_in_game: number;
}

export const fetchHandAnalytics = async (publicCode: string): Promise<HandAnalyticsResponse> => {
  const response = await axios.get(
    `${API_BASE_URL}/api/games/${publicCode}/hand-analytics`
  );
  return response.data;
};

export function useHandAnalytics(publicCode: string) {
  return useQuery(
    ["handAnalytics", publicCode],
    () => fetchHandAnalytics(publicCode),
    {
      enabled: !!publicCode,
      refetchOnWindowFocus: false,
    }
  );
}