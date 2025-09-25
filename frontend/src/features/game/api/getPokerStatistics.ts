import { useQuery } from "react-query";
import { API_BASE_URL } from "../../../config/api";

export interface PlayerStatistic {
  playerId: string;
  playerName: string;
  handsPlayed: number;
  vpip: number;
  pfr: number;
  aggressionFrequency: number;
  playStyle: string;
  styleColor?: string;
  styleDescription?: string;
  vpipCategory?: string;
  pfrCategory?: string;
  afCategory?: string;
  flopAF: number;
  turnAF: number;
  riverAF: number;
}

export interface GameStatisticsConfig {
  configType: string;
  description: string;
  thresholds: {
    vpip: {
      tight: string;
      normal: string;
      loose: string;
      veryLoose: string;
    };
    pfr: {
      passive: string;
      normal: string;
      aggressive: string;
      veryAggressive: string;
    };
    af: {
      passive: string;
      normal: string;
      aggressive: string;
    };
  };
}

export interface AdaptiveStatisticsResponse {
  config: GameStatisticsConfig;
  players: PlayerStatistic[];
}

export interface SessionStatisticsResponse {
  session_id: string;
  session_name?: string;
  game_number?: number;
  players: PlayerStatistic[];
}

export interface PlayerOverallStatistics {
  player: {
    playerId: string;
    playerName: string;
    overall: {
      totalHands: number;
      vpip: number;
      pfr: number;
      aggressionFrequency: number;
      playStyle: string;
    };
    bySession: Array<{
      sessionId: string;
      gameNumber: number;
      sessionName?: string;
      handsPlayed: number;
      vpip: number;
      pfr: number;
      aggressionFrequency: number;
      playStyle: string;
    }>;
  };
}

/**
 * Fetch poker statistics for all players in a specific session
 */
export const useSessionStatistics = (publicCode: string, sessionId: string) => {
  return useQuery<SessionStatisticsResponse>({
    queryKey: ["session-statistics", publicCode, sessionId],
    queryFn: async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/games/${publicCode}/sessions/${sessionId}/statistics`
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to fetch session statistics");
      }

      return response.json();
    },
    enabled: !!publicCode && !!sessionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Fetch poker statistics for a specific player across all sessions in a game
 */
export const usePlayerStatistics = (publicCode: string, playerId: string) => {
  return useQuery<PlayerOverallStatistics>({
    queryKey: ["player-statistics", publicCode, playerId],
    queryFn: async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/games/${publicCode}/players/${playerId}/statistics`
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to fetch player statistics");
      }

      return response.json();
    },
    enabled: !!publicCode && !!playerId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Fetch aggregated poker statistics for all players across all sessions in a game
 */
export const usePokerStatistics = (publicCode: string) => {
  return useQuery<PlayerStatistic[]>({
    queryKey: ["poker-statistics", publicCode],
    queryFn: async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/games/${publicCode}/statistics`
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to fetch poker statistics");
      }

      return response.json();
    },
    enabled: !!publicCode,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Fetch adaptive poker statistics with game-type-specific classification
 */
export const useAdaptivePokerStatistics = (publicCode: string) => {
  return useQuery<AdaptiveStatisticsResponse>({
    queryKey: ["adaptive-poker-statistics", publicCode],
    queryFn: async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/games/${publicCode}/statistics/adaptive`
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to fetch adaptive poker statistics");
      }

      return response.json();
    },
    enabled: !!publicCode,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Calculate/recalculate poker statistics for a session (admin only)
 */
export const calculateSessionStatistics = async (
  publicCode: string,
  sessionId: string,
  adminCode: string
) => {
  const response = await fetch(
    `${API_BASE_URL}/api/games/${publicCode}/sessions/${sessionId}/statistics/calculate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Code": adminCode,
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to calculate session statistics");
  }

  return response.json();
};