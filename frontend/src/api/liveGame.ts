/**
 * Live Game API Client and React Query Hooks
 *
 * Provides API client functions and custom hooks for managing real-time
 * live poker game sessions, including game creation, participant management,
 * transaction handling, and game closure.
 */

import { useQuery, useMutation, useQueryClient } from 'react-query';
import type {
  LiveGame,
  Participant,
  LiveGameTransaction,
  GameSummary,
  CreateLiveGameRequest,
  CreateLiveGameResponse,
  ActiveLiveGameResponse,
  JoinLiveGameRequest,
  JoinLiveGameResponse,
  ClaimAndJoinRequest,
  TransactionRequest,
  TransactionResponse,
  ApproveTransactionResponse,
  RejectTransactionRequest,
  RejectTransactionResponse,
  EditTransactionRequest,
  EditTransactionResponse,
  CloseLiveGameResponse,
} from '../types/liveGame';
import { apiClient } from './client';

// ============================================================================
// API Client Functions
// ============================================================================

/**
 * Create a new live game session for a parent game
 */
export async function createLiveGame(
  gameId: string,
  data: CreateLiveGameRequest
): Promise<CreateLiveGameResponse> {
  const response = await apiClient.post<any>(`/api/games/${gameId}/live-games`, {
    small_blind: data.smallBlind,
    big_blind: data.bigBlind,
    min_buy_in: data.minBuyIn,
    max_buy_in: data.maxBuyIn,
  });

  // Transform snake_case to camelCase
  return {
    liveGameId: response.data.live_game_id,
    gameId: response.data.game_id,
    joinCode: response.data.join_code,
    status: response.data.status,
    createdByUserId: response.data.created_by_user_id,
    smallBlind: response.data.small_blind,
    bigBlind: response.data.big_blind,
    minBuyIn: response.data.min_buy_in,
    maxBuyIn: response.data.max_buy_in,
    startedAt: response.data.started_at,
  };
}

/**
 * Get active live game for a parent game
 */
export async function getActiveLiveGame(gameId: string): Promise<ActiveLiveGameResponse | null> {
  try {
    const response = await apiClient.get<any>(`/api/games/${gameId}/live-games/active`);

    // Transform snake_case to camelCase
    return {
      liveGameId: response.data.live_game_id,
      joinCode: response.data.join_code,
      status: response.data.status,
      startedAt: response.data.started_at,
      participantCount: response.data.participant_count,
    };
  } catch (error: any) {
    // Return null if no active game found (404)
    if (error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

/**
 * Get active live game for a parent game using public code
 */
export async function getActiveLiveGameByPublicCode(publicCode: string): Promise<ActiveLiveGameResponse | null> {
  try {
    const response = await apiClient.get<any>(`/api/games/public/${publicCode}/live-games/active`);

    // Transform snake_case to camelCase
    return {
      liveGameId: response.data.live_game_id,
      gameId: response.data.game_id,
      joinCode: response.data.join_code,
      status: response.data.status,
      startedAt: response.data.started_at,
      participantCount: response.data.participant_count,
    };
  } catch (error: any) {
    // Return null if no active game found (404)
    if (error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

/**
 * Get live game details by join code
 */
export async function getLiveGameInfo(joinCode: string): Promise<LiveGame> {
  const response = await apiClient.get<any>(`/api/live-games/${joinCode}`);

  // Store joinCode -> publicCode mapping for admin session checks
  if (response.data.public_code) {
    try {
      const mappingStr = localStorage.getItem('join_code_to_public_code') || '{}';
      const mapping = JSON.parse(mappingStr);
      mapping[response.data.join_code] = response.data.public_code;
      localStorage.setItem('join_code_to_public_code', JSON.stringify(mapping));
    } catch (error) {
      // Silently handle storage errors
    }
  }

  // Transform snake_case to camelCase
  return {
    liveGameId: response.data.live_game_id,
    gameId: response.data.game_id,
    publicCode: response.data.public_code,
    joinCode: response.data.join_code,
    status: response.data.status,
    createdByUserId: response.data.created_by_user_id,
    smallBlind: response.data.small_blind,
    bigBlind: response.data.big_blind,
    minBuyIn: response.data.min_buy_in,
    maxBuyIn: response.data.max_buy_in,
    startedAt: response.data.started_at,
    closedAt: response.data.closed_at,
  };
}

/**
 * Join a live game using a join code
 *
 * Response variants:
 * 1. alreadyJoined: User has already joined this live game
 * 2. autoLinked: User was auto-linked to existing claimed player
 * 3. needsClaim: User needs to claim a player identity
 * 4. Regular join: Direct join without claiming (legacy behavior)
 */
export async function joinLiveGame(data: JoinLiveGameRequest): Promise<JoinLiveGameResponse> {
  const response = await apiClient.post<any>('/api/live-games/join', {
    join_code: data.joinCode,
    display_name: data.displayName,
  });

  // Transform snake_case to camelCase, handling all response variants
  const result: JoinLiveGameResponse = {
    participantId: response.data.participant_id,
    liveGameId: response.data.live_game_id,
    userId: response.data.user_id,
    displayName: response.data.display_name,
    joinedAt: response.data.joined_at,
    playerId: response.data.player_id,
    alreadyJoined: response.data.already_joined,
    autoLinked: response.data.auto_linked,
    needsClaim: response.data.needs_claim,
  };

  // Transform player info if present
  if (response.data.player) {
    result.player = {
      id: response.data.player.id,
      name: response.data.player.name,
    };
  }

  // Transform available players if present
  if (response.data.available_players) {
    result.availablePlayers = response.data.available_players.map((p: any) => ({
      playerId: p.player_id,
      playerName: p.player_name,
      sessionCount: p.session_count,
    }));
  }

  return result;
}

/**
 * Claim a player identity and join live game atomically
 *
 * Two modes:
 * 1. Claim existing player: Provide playerId
 * 2. Create new player: Provide newPlayerName
 *
 * @param joinCode - 4-character join code
 * @param data - Request data with playerId OR newPlayerName (mutually exclusive)
 */
export async function claimAndJoinLiveGame(
  joinCode: string,
  data: ClaimAndJoinRequest
): Promise<JoinLiveGameResponse> {
  const requestBody: any = {
    display_name: data.displayName,
  };

  // Add either player_id or new_player_name (mutually exclusive)
  if (data.playerId) {
    requestBody.player_id = data.playerId;
  } else if (data.newPlayerName) {
    requestBody.new_player_name = data.newPlayerName;
  }

  const response = await apiClient.post<any>(
    `/api/live-games/${joinCode}/claim-and-join`,
    requestBody
  );

  // Transform snake_case to camelCase
  const result: JoinLiveGameResponse = {
    participantId: response.data.participant_id,
    liveGameId: response.data.live_game_id,
    userId: response.data.user_id,
    displayName: response.data.display_name,
    joinedAt: response.data.joined_at,
    playerId: response.data.player_id,
  };

  // Transform player info if present
  if (response.data.player) {
    result.player = {
      id: response.data.player.id,
      name: response.data.player.name,
    };
  }

  return result;
}

/**
 * Get all participants with current statistics
 */
export async function getParticipants(joinCode: string): Promise<Participant[]> {
  const response = await apiClient.get<any>(`/api/live-games/${joinCode}/participants`);

  // Transform snake_case to camelCase
  return response.data.participants.map((p: any) => ({
    participantId: p.participant_id,
    userId: p.user_id,
    displayName: p.display_name,
    joinedAt: p.joined_at,
    stats: {
      totalBuyIns: p.stats.total_buy_ins,
      totalCashOuts: p.stats.total_cash_outs,
      netResult: p.stats.net_result,
      chipsOnTable: p.stats.chips_on_table,
    },
  }));
}

/**
 * Request a buy-in transaction
 */
export async function requestBuyIn(
  joinCode: string,
  data: TransactionRequest
): Promise<TransactionResponse> {
  const response = await apiClient.post<any>(
    `/api/live-games/${joinCode}/transactions/buy-in`,
    { amount: data.amount }
  );

  // Transform snake_case to camelCase
  return {
    transactionId: response.data.transaction_id,
    liveGameId: response.data.live_game_id,
    participantId: response.data.participant_id,
    userId: response.data.user_id,
    transactionType: response.data.transaction_type,
    amount: response.data.amount,
    status: response.data.status,
    createdAt: response.data.created_at,
  };
}

/**
 * Request a cash-out transaction
 */
export async function requestCashOut(
  joinCode: string,
  data: TransactionRequest
): Promise<TransactionResponse> {
  const response = await apiClient.post<any>(
    `/api/live-games/${joinCode}/transactions/cash-out`,
    { amount: data.amount }
  );

  // Transform snake_case to camelCase
  return {
    transactionId: response.data.transaction_id,
    liveGameId: response.data.live_game_id,
    participantId: response.data.participant_id,
    userId: response.data.user_id,
    transactionType: response.data.transaction_type,
    amount: response.data.amount,
    status: response.data.status,
    createdAt: response.data.created_at,
  };
}

/**
 * Get all pending transactions for a live game
 * Requires admin permission (creator or game owner)
 */
export async function getPendingTransactions(joinCode: string): Promise<LiveGameTransaction[]> {
  const response = await apiClient.get<any>(`/api/live-games/${joinCode}/transactions/pending`);

  // Transform snake_case to camelCase
  return response.data.pending_transactions.map((t: any) => ({
    transactionId: t.transaction_id,
    liveGameId: t.live_game_id,
    participantId: t.participant_id,
    userId: t.user_id,
    transactionType: t.transaction_type,
    amount: t.amount,
    originalAmount: t.original_amount,
    status: t.status,
    createdAt: t.created_at,
    approvedByUserId: t.approved_by_user_id,
    approvedAt: t.approved_at,
    rejectedByUserId: t.rejected_by_user_id,
    rejectedAt: t.rejected_at,
    rejectionReason: t.rejection_reason,
    editedByUserId: t.edited_by_user_id,
    editedAt: t.edited_at,
    editReason: t.edit_reason,
  }));
}

/**
 * Approve a pending transaction
 * Requires admin permission (creator or game owner)
 */
export async function approveTransaction(transactionId: string): Promise<ApproveTransactionResponse> {
  const response = await apiClient.patch<any>(
    `/api/live-games/transactions/${transactionId}/approve`,
    {}
  );

  // Transform snake_case to camelCase
  return {
    transactionId: response.data.transaction_id,
    status: response.data.status,
    approvedByUserId: response.data.approved_by_user_id,
    approvedAt: response.data.approved_at,
  };
}

/**
 * Reject a pending transaction
 * Requires admin permission (creator or game owner)
 */
export async function rejectTransaction(
  transactionId: string,
  data: RejectTransactionRequest
): Promise<RejectTransactionResponse> {
  const response = await apiClient.patch<any>(
    `/api/live-games/transactions/${transactionId}/reject`,
    { reason: data.reason }
  );

  // Transform snake_case to camelCase
  return {
    transactionId: response.data.transaction_id,
    status: response.data.status,
    rejectedByUserId: response.data.rejected_by_user_id,
    rejectedAt: response.data.rejected_at,
    rejectionReason: response.data.rejection_reason,
  };
}

/**
 * Edit transaction amount (preserves original for audit)
 * Requires admin permission (creator or game owner)
 */
export async function editTransactionAmount(
  transactionId: string,
  data: EditTransactionRequest
): Promise<EditTransactionResponse> {
  const response = await apiClient.patch<any>(`/api/live-games/transactions/${transactionId}`, {
    new_amount: data.newAmount,
    reason: data.reason,
  });

  // Transform snake_case to camelCase
  return {
    transactionId: response.data.transaction_id,
    amount: response.data.amount,
    originalAmount: response.data.original_amount,
    editedByUserId: response.data.edited_by_user_id,
    editedAt: response.data.edited_at,
    editReason: response.data.edit_reason,
  };
}

/**
 * Close a live game with validation
 * Requires admin permission (creator or game owner)
 * Validates: all players cashed out, game is balanced
 * Automatically creates a session in the parent game's ledger
 *
 * @param confirmedZeroPlayers - Array of participant IDs confirmed to have $0 (auto-creates cash-outs)
 */
export async function closeLiveGame(
  joinCode: string,
  confirmedZeroPlayers?: string[]
): Promise<CloseLiveGameResponse> {
  const requestBody = confirmedZeroPlayers ? { confirmed_zero_players: confirmedZeroPlayers } : {};
  const response = await apiClient.post<any>(`/api/live-games/${joinCode}/close`, requestBody);

  // Transform snake_case to camelCase
  return {
    liveGameId: response.data.live_game_id,
    status: response.data.status,
    closedAt: response.data.closed_at,
    summary: {
      totalBuyIns: response.data.summary.total_buy_ins,
      totalCashOuts: response.data.summary.total_cash_outs,
      isBalanced: response.data.summary.is_balanced,
    },
    // Optional session creation fields
    sessionCreated: response.data.session_created,
    sessionId: response.data.session_id,
    gameNumber: response.data.game_number,
  };
}

/**
 * Get complete game summary for reconciliation
 */
export async function getGameSummary(joinCode: string): Promise<GameSummary> {
  const response = await apiClient.get<any>(`/api/live-games/${joinCode}/summary`);

  // Transform snake_case to camelCase
  return {
    liveGameId: response.data.live_game_id,
    status: response.data.status,
    startedAt: response.data.started_at,
    closedAt: response.data.closed_at,
    totalBuyIns: response.data.total_buy_ins,
    totalCashOuts: response.data.total_cash_outs,
    difference: response.data.difference,
    isBalanced: response.data.is_balanced,
    participants: response.data.participants.map((p: any) => ({
      displayName: p.display_name,
      stats: {
        totalBuyIns: p.stats.total_buy_ins,
        totalCashOuts: p.stats.total_cash_outs,
        netResult: p.stats.net_result,
        chipsOnTable: p.stats.chips_on_table,
      },
    })),
  };
}

// ============================================================================
// Query Keys
// ============================================================================

export const liveGameKeys = {
  all: ['liveGames'] as const,
  active: (gameId: string) => ['liveGames', 'active', gameId] as const,
  activeByPublicCode: (publicCode: string) => ['liveGames', 'active', 'public', publicCode] as const,
  info: (joinCode: string) => ['liveGames', 'info', joinCode] as const,
  participants: (joinCode: string) => ['liveGames', 'participants', joinCode] as const,
  pendingTransactions: (joinCode: string) => ['liveGames', 'pending', joinCode] as const,
  summary: (joinCode: string) => ['liveGames', 'summary', joinCode] as const,
};

// ============================================================================
// React Query Hooks - Queries
// ============================================================================

/**
 * Hook to fetch active live game for a parent game
 * @param gameId - Parent game ID. Query is disabled if null/undefined
 */
export function useActiveLiveGame(gameId: string | undefined) {
  return useQuery(
    liveGameKeys.active(gameId!),
    () => getActiveLiveGame(gameId!),
    {
      enabled: !!gameId,
      refetchOnWindowFocus: false,
      staleTime: 30000, // 30 seconds
    }
  );
}

/**
 * Hook to fetch active live game for a parent game using public code
 * @param publicCode - Parent game public code (5-char alphanumeric). Query is disabled if null/undefined
 */
export function useActiveLiveGameByPublicCode(publicCode: string | undefined) {
  return useQuery(
    liveGameKeys.activeByPublicCode(publicCode!),
    () => getActiveLiveGameByPublicCode(publicCode!),
    {
      enabled: !!publicCode,
      refetchOnWindowFocus: false,
      staleTime: 30000, // 30 seconds
      retry: false, // Don't retry - 404 is expected when no active game exists
      onError: (error: any) => {
        // Suppress 404 errors - this is expected when no active game exists
        if (error?.response?.status === 404) {
          return; // Silently handle - API function returns null for 404s
        }
        // Silently handle other errors
      },
    }
  );
}

/**
 * Hook to fetch live game information by join code
 * @param joinCode - 4-character join code. Query is disabled if null/undefined
 */
export function useLiveGameInfo(joinCode: string | undefined) {
  return useQuery(
    liveGameKeys.info(joinCode!),
    () => getLiveGameInfo(joinCode!),
    {
      enabled: !!joinCode,
      refetchOnWindowFocus: false,
      staleTime: 30000, // 30 seconds
      retry: (failureCount, error: any) => {
        // Don't retry 410 (game closed) or 404 (not found) - these are final states
        if (error?.response?.status === 410 || error?.response?.status === 404) {
          return false;
        }
        // Retry other errors up to 3 times
        return failureCount < 3;
      },
      onError: (error: any) => {
        const status = error?.response?.status;
        // Suppress expected errors (410 = closed, 404 = not found)
        // Components handle these via error state for redirects/UI
        if (status === 410 || status === 404) {
          return; // Silently handle
        }
        // Silently handle unexpected errors
      },
    }
  );
}

/**
 * Hook to fetch participants with current statistics
 * @param joinCode - 4-character join code. Query is disabled if null/undefined
 */
export function useParticipants(joinCode: string | undefined) {
  return useQuery(
    liveGameKeys.participants(joinCode!),
    () => getParticipants(joinCode!),
    {
      enabled: !!joinCode,
      refetchOnWindowFocus: false,
      // Real-time updates via SSE (no polling needed)
    }
  );
}

/**
 * Hook to fetch pending transactions (admin only)
 * @param joinCode - 4-character join code. Query is disabled if null/undefined
 */
export function usePendingTransactions(joinCode: string | undefined) {
  return useQuery(
    liveGameKeys.pendingTransactions(joinCode!),
    () => getPendingTransactions(joinCode!),
    {
      enabled: !!joinCode,
      refetchOnWindowFocus: false,
      // Real-time updates via SSE (no polling needed)
      retry: 1, // Only retry once (may get 403 if not admin)
    }
  );
}

/**
 * Hook to fetch game summary
 * @param joinCode - 4-character join code. Query is disabled if null/undefined
 */
export function useGameSummary(joinCode: string | undefined) {
  return useQuery(
    liveGameKeys.summary(joinCode!),
    () => getGameSummary(joinCode!),
    {
      enabled: !!joinCode,
      refetchOnWindowFocus: false,
    }
  );
}

// ============================================================================
// React Query Hooks - Mutations
// ============================================================================

/**
 * Hook to create a new live game
 * @example
 * const createMutation = useCreateLiveGame();
 * createMutation.mutate({ gameId: 'uuid', data: { minBuyIn: 20 } });
 */
export function useCreateLiveGame() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ gameId, data }: { gameId: string; data: CreateLiveGameRequest }) =>
      createLiveGame(gameId, data),
    {
      onSuccess: (_, variables) => {
        // Invalidate active live game query
        queryClient.invalidateQueries(liveGameKeys.active(variables.gameId));
      },
    }
  );
}

/**
 * Hook to join a live game
 * @example
 * const joinMutation = useJoinLiveGame();
 * joinMutation.mutate({ joinCode: 'A3B7', displayName: 'John Doe' });
 */
export function useJoinLiveGame() {
  const queryClient = useQueryClient();

  return useMutation(
    (data: JoinLiveGameRequest) => joinLiveGame(data),
    {
      onSuccess: (_, variables) => {
        // Invalidate participants list
        queryClient.invalidateQueries(liveGameKeys.participants(variables.joinCode));
      },
    }
  );
}

/**
 * Hook to claim a player identity and join live game
 * @example
 * // Claim existing player
 * const claimMutation = useClaimAndJoinLiveGame();
 * claimMutation.mutate({
 *   joinCode: 'A3B7',
 *   data: { playerId: 'uuid', displayName: 'John Doe' }
 * });
 *
 * // Create new player
 * claimMutation.mutate({
 *   joinCode: 'A3B7',
 *   data: { newPlayerName: 'JohnD', displayName: 'John Doe' }
 * });
 */
export function useClaimAndJoinLiveGame() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ joinCode, data }: { joinCode: string; data: ClaimAndJoinRequest }) =>
      claimAndJoinLiveGame(joinCode, data),
    {
      onSuccess: (_, variables) => {
        // Invalidate participants list
        queryClient.invalidateQueries(liveGameKeys.participants(variables.joinCode));
      },
    }
  );
}

/**
 * Hook to request a buy-in
 * @example
 * const buyInMutation = useRequestBuyIn();
 * buyInMutation.mutate({ joinCode: 'A3B7', amount: 50 });
 */
export function useRequestBuyIn() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ joinCode, amount }: { joinCode: string; amount: number }) =>
      requestBuyIn(joinCode, { amount }),
    {
      onSuccess: (_, variables) => {
        // Invalidate pending transactions and participants
        queryClient.invalidateQueries(liveGameKeys.pendingTransactions(variables.joinCode));
        queryClient.invalidateQueries(liveGameKeys.participants(variables.joinCode));
      },
    }
  );
}

/**
 * Hook to request a cash-out
 * @example
 * const cashOutMutation = useRequestCashOut();
 * cashOutMutation.mutate({ joinCode: 'A3B7', amount: 75 });
 */
export function useRequestCashOut() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ joinCode, amount }: { joinCode: string; amount: number }) =>
      requestCashOut(joinCode, { amount }),
    {
      onSuccess: (_, variables) => {
        // Invalidate pending transactions and participants
        queryClient.invalidateQueries(liveGameKeys.pendingTransactions(variables.joinCode));
        queryClient.invalidateQueries(liveGameKeys.participants(variables.joinCode));
      },
    }
  );
}

/**
 * Hook to approve a transaction (admin only)
 * @example
 * const approveMutation = useApproveTransaction();
 * approveMutation.mutate({ joinCode: 'A3B7', transactionId: 'uuid' });
 */
export function useApproveTransaction() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ transactionId }: { joinCode: string; transactionId: string }) =>
      approveTransaction(transactionId),
    {
      onSuccess: (_, variables) => {
        // Invalidate all relevant queries
        queryClient.invalidateQueries(liveGameKeys.pendingTransactions(variables.joinCode));
        queryClient.invalidateQueries(liveGameKeys.participants(variables.joinCode));
        queryClient.invalidateQueries(liveGameKeys.summary(variables.joinCode));
      },
    }
  );
}

/**
 * Hook to reject a transaction (admin only)
 * @example
 * const rejectMutation = useRejectTransaction();
 * rejectMutation.mutate({ joinCode: 'A3B7', transactionId: 'uuid', reason: 'Incorrect amount' });
 */
export function useRejectTransaction() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ transactionId, reason }: { joinCode: string; transactionId: string; reason: string }) =>
      rejectTransaction(transactionId, { reason }),
    {
      onSuccess: (_, variables) => {
        // Invalidate pending transactions
        queryClient.invalidateQueries(liveGameKeys.pendingTransactions(variables.joinCode));
      },
    }
  );
}

/**
 * Hook to edit a transaction amount (admin only)
 * @example
 * const editMutation = useEditTransaction();
 * editMutation.mutate({ joinCode: 'A3B7', transactionId: 'uuid', newAmount: 60, reason: 'Correction' });
 */
export function useEditTransaction() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ transactionId, newAmount, reason }: {
      joinCode: string;
      transactionId: string;
      newAmount: number;
      reason: string;
    }) => editTransactionAmount(transactionId, { newAmount, reason }),
    {
      onSuccess: (_, variables) => {
        // Invalidate all relevant queries
        queryClient.invalidateQueries(liveGameKeys.pendingTransactions(variables.joinCode));
        queryClient.invalidateQueries(liveGameKeys.participants(variables.joinCode));
        queryClient.invalidateQueries(liveGameKeys.summary(variables.joinCode));
      },
    }
  );
}

/**
 * Hook to close a live game (admin only)
 * @example
 * const closeMutation = useCloseLiveGame();
 * closeMutation.mutate({ joinCode: 'A3B7', confirmedZeroPlayers: ['uuid1', 'uuid2'] });
 */
export function useCloseLiveGame() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ joinCode, confirmedZeroPlayers }: { joinCode: string; confirmedZeroPlayers?: string[] }) =>
      closeLiveGame(joinCode, confirmedZeroPlayers),
    {
      onSuccess: (_, { joinCode }) => {
        // Invalidate all queries for this game
        queryClient.invalidateQueries(liveGameKeys.info(joinCode));
        queryClient.invalidateQueries(liveGameKeys.participants(joinCode));
        queryClient.invalidateQueries(liveGameKeys.summary(joinCode));
      },
    }
  );
}
