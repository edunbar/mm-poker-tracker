/**
 * Live Game Type Definitions
 *
 * TypeScript interfaces for real-time live poker game tracking.
 * All property names use camelCase (frontend convention).
 */

export interface LiveGame {
  liveGameId: string;
  gameId: string;
  publicCode?: string; // Parent game's public code for admin session checks
  joinCode: string;
  status: 'active' | 'closed';
  createdByUserId: string;
  smallBlind: number | null;
  bigBlind: number | null;
  minBuyIn: number;
  maxBuyIn: number | null;
  startedAt: string; // ISO date string
  closedAt: string | null; // ISO date string
}

export interface ParticipantStats {
  totalBuyIns: number;
  totalCashOuts: number;
  netResult: number;
  chipsOnTable: number;
}

export interface Participant {
  participantId: string;
  userId: string;
  displayName: string;
  joinedAt: string; // ISO date string
  stats: ParticipantStats;
}

export interface LiveGameTransaction {
  transactionId: string;
  liveGameId: string;
  participantId: string;
  userId: string;
  transactionType: 'buy_in' | 'cash_out';
  amount: number;
  originalAmount: number | null;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string; // ISO date string
  approvedByUserId: string | null;
  approvedAt: string | null; // ISO date string
  rejectedByUserId: string | null;
  rejectedAt: string | null; // ISO date string
  rejectionReason: string | null;
  editedByUserId: string | null;
  editedAt: string | null; // ISO date string
  editReason: string | null;
}

export interface GameSummary {
  liveGameId: string;
  status: string;
  startedAt: string; // ISO date string
  closedAt: string | null; // ISO date string
  totalBuyIns: number;
  totalCashOuts: number;
  difference: number;
  isBalanced: boolean;
  participants: Array<{
    displayName: string;
    stats: ParticipantStats;
  }>;
}

// ============================================================================
// Request/Response Interfaces
// ============================================================================

export interface CreateLiveGameRequest {
  smallBlind?: number;
  bigBlind?: number;
  minBuyIn: number;
  maxBuyIn?: number;
}

export interface CreateLiveGameResponse {
  liveGameId: string;
  gameId: string;
  joinCode: string;
  status: 'active' | 'closed';
  createdByUserId: string;
  smallBlind: number | null;
  bigBlind: number | null;
  minBuyIn: number;
  maxBuyIn: number | null;
  startedAt: string;
}

export interface ActiveLiveGameResponse {
  liveGameId: string;
  gameId?: string; // Only present when fetched by public code
  joinCode: string;
  status: 'active';
  startedAt: string;
  participantCount: number;
}

export interface JoinLiveGameRequest {
  joinCode: string;
  displayName: string;
}

export interface AvailablePlayer {
  playerId: string;
  playerName: string;
  sessionCount: number;
}

export interface PlayerInfo {
  id: string;
  name: string;
}

export interface JoinLiveGameResponse {
  participantId?: string;
  liveGameId?: string;
  userId?: string;
  displayName?: string;
  joinedAt?: string;
  // Player identity claiming fields
  alreadyJoined?: boolean;
  autoLinked?: boolean;
  needsClaim?: boolean;
  availablePlayers?: AvailablePlayer[];
  player?: PlayerInfo;
  playerId?: string;
}

export interface ClaimAndJoinRequest {
  playerId?: string;
  newPlayerName?: string;
  displayName: string;
}

export interface TransactionRequest {
  amount: number;
}

export interface TransactionResponse {
  transactionId: string;
  liveGameId: string;
  participantId: string;
  userId: string;
  transactionType: 'buy_in' | 'cash_out';
  amount: number;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
}

export interface ApproveTransactionResponse {
  transactionId: string;
  status: 'approved';
  approvedByUserId: string;
  approvedAt: string;
}

export interface RejectTransactionRequest {
  reason: string;
}

export interface RejectTransactionResponse {
  transactionId: string;
  status: 'rejected';
  rejectedByUserId: string;
  rejectedAt: string;
  rejectionReason: string;
}

export interface EditTransactionRequest {
  newAmount: number;
  reason: string;
}

export interface EditTransactionResponse {
  transactionId: string;
  amount: number;
  originalAmount: number | null;
  editedByUserId: string;
  editedAt: string;
  editReason: string;
}

export interface CloseLiveGameResponse {
  liveGameId: string;
  status: 'closed';
  closedAt: string;
  summary: {
    totalBuyIns: number;
    totalCashOuts: number;
    isBalanced: boolean;
  };
  // Session creation fields (optional - may not be present if creation failed)
  sessionCreated?: boolean;
  sessionId?: string;
  gameNumber?: number;
}

export interface UncashedPlayer {
  participantId: string;
  displayName: string;
  totalBuyIns: number;
  chipsOnTable: number;
}

export interface CloseLiveGameErrorResponse {
  error: string;
  uncashedPlayers: UncashedPlayer[];
}
