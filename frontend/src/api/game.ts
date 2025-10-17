/**
 * Game API Client and React Query Hooks
 *
 * Provides API client functions and custom hooks for fetching game information.
 */

import { useQuery } from 'react-query';
import { apiClient } from './client';

// ============================================================================
// Types
// ============================================================================

export interface GameInfo {
  gameId: string;
  publicCode: string;
  title: string | null;
}

// ============================================================================
// API Client Functions
// ============================================================================

/**
 * Get basic game information by public code
 */
export async function getGameInfoByPublicCode(publicCode: string): Promise<GameInfo> {
  const response = await apiClient.get<any>(`/api/games/public/${publicCode}/info`);

  return {
    gameId: response.data.game_id,
    publicCode: response.data.public_code,
    title: response.data.title,
  };
}

// ============================================================================
// Query Keys
// ============================================================================

export const gameKeys = {
  all: ['games'] as const,
  info: (publicCode: string) => ['games', 'info', publicCode] as const,
};

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Hook to fetch game information by public code
 * @param publicCode - Public game code (5-char alphanumeric). Query is disabled if null/undefined
 */
export function useGameInfo(publicCode: string | undefined) {
  return useQuery(
    gameKeys.info(publicCode!),
    () => getGameInfoByPublicCode(publicCode!),
    {
      enabled: !!publicCode,
      refetchOnWindowFocus: false,
      staleTime: 60000, // 1 minute
    }
  );
}
