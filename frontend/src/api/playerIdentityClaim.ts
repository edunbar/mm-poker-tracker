import { useQuery, useMutation } from 'react-query';
import { apiClient } from './client';

// ============================================================================
// TypeScript Interfaces
// ============================================================================

export interface PlayerIdentityClaim {
  claimId: string;
  playerId: string;
  playerName: string;
  claimedAt: string; // ISO date string
  verificationMethod: string;
  games: Array<{
    gameId: string;
    publicCode: string;
    gameTitle: string;
  }>;
}

export interface ClaimablePlayer {
  playerId: string;
  playerName: string;
  sessionCount: number;
}

export interface PlayerPreview {
  playerId: string;
  playerName: string;
  sessionCount: number;
}

// ============================================================================
// API Client Functions
// ============================================================================

/**
 * Get all player identity claims for the current authenticated user
 */
export async function getMyPlayerClaims(): Promise<PlayerIdentityClaim[]> {
  const response = await apiClient.get<{
    claims: Array<{
      claim_id: string;
      player_id: string;
      player_name: string;
      claimed_at: string;
      verification_method: string;
      games: Array<{
        game_id: string;
        public_code: string;
        game_title: string;
      }>;
    }>;
  }>('/api/player-identity-claims/me');

  // Transform snake_case to camelCase
  return response.data.claims.map((claim) => ({
    claimId: claim.claim_id,
    playerId: claim.player_id,
    playerName: claim.player_name,
    claimedAt: claim.claimed_at,
    verificationMethod: claim.verification_method,
    games: claim.games.map((game) => ({
      gameId: game.game_id,
      publicCode: game.public_code,
      gameTitle: game.game_title,
    })),
  }));
}

/**
 * Get all unclaimed players in a specific game
 */
export async function getClaimablePlayers(gameId: string): Promise<ClaimablePlayer[]> {
  const response = await apiClient.get<{
    claimable_players: Array<{
      player_id: string;
      player_name: string;
      session_count: number;
    }>;
  }>(`/api/player-identity-claims/games/${gameId}/claimable`);

  // Transform snake_case to camelCase
  return response.data.claimable_players.map((player) => ({
    playerId: player.player_id,
    playerName: player.player_name,
    sessionCount: player.session_count,
  }));
}

/**
 * Get preview information for a player before claiming
 */
export async function getPlayerPreview(playerId: string): Promise<PlayerPreview> {
  const response = await apiClient.get<{
    player_id: string;
    player_name: string;
    session_count: number;
  }>(`/api/player-identity-claims/players/${playerId}/preview`);

  // Transform snake_case to camelCase
  return {
    playerId: response.data.player_id,
    playerName: response.data.player_name,
    sessionCount: response.data.session_count,
  };
}

/**
 * Claim a player identity
 */
export async function claimPlayerIdentity(
  playerId: string,
  verificationMethod = 'manual'
): Promise<void> {
  await apiClient.post('/api/player-identity-claims/claim', {
    player_id: playerId,
    verification_method: verificationMethod,
  });
}

/**
 * Unclaim a player identity
 */
export async function unclaimPlayerIdentity(claimId: string): Promise<void> {
  await apiClient.delete(`/api/player-identity-claims/${claimId}`);
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Hook to fetch all player identity claims for the current user
 */
export function useMyPlayerClaims() {
  return useQuery(['playerIdentityClaims', 'me'], getMyPlayerClaims, {
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to fetch claimable players in a specific game
 * @param gameId - Game ID (UUID). Query is disabled if null/undefined
 */
export function useClaimablePlayers(gameId: string | null) {
  return useQuery(
    ['playerIdentityClaims', 'claimable', gameId],
    () => getClaimablePlayers(gameId!),
    {
      enabled: !!gameId,
      refetchOnWindowFocus: false,
    }
  );
}

/**
 * Hook to fetch player preview information
 * @param playerId - Player ID (UUID). Query is disabled if null/undefined
 */
export function usePlayerPreview(playerId: string | null) {
  return useQuery(
    ['playerIdentityClaims', 'preview', playerId],
    () => getPlayerPreview(playerId!),
    {
      enabled: !!playerId,
      refetchOnWindowFocus: false,
    }
  );
}

/**
 * Hook to claim a player identity
 * @returns Mutation object with mutate function
 * @example
 * const claimMutation = useClaimPlayer();
 * claimMutation.mutate({ playerId: 'uuid', verificationMethod: 'manual' });
 */
export function useClaimPlayer() {
  return useMutation(
    ({ playerId, verificationMethod = 'manual' }: { playerId: string; verificationMethod?: string }) =>
      claimPlayerIdentity(playerId, verificationMethod)
  );
}

/**
 * Hook to unclaim a player identity
 * @returns Mutation object with mutate function
 * @example
 * const unclaimMutation = useUnclaimPlayer();
 * unclaimMutation.mutate('claim-uuid');
 */
export function useUnclaimPlayer() {
  return useMutation(unclaimPlayerIdentity);
}
