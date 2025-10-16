/**
 * useLiveGameSSE - Real-Time Updates via Server-Sent Events
 *
 * Custom React hook for establishing SSE connection to receive live game updates.
 * Replaces polling with instant event-driven updates.
 *
 * Features:
 * - Auto-reconnection with exponential backoff (1s → 30s, max 10 retries)
 * - Automatic query invalidation via React Query
 * - Connection cleanup on unmount
 * - Event handlers for all live game event types
 *
 * Event Types:
 * - participant_joined: New player joined
 * - transaction_created: Buy-in/cash-out requested
 * - transaction_approved: Transaction approved by admin
 * - transaction_rejected: Transaction rejected by admin
 * - transaction_edited: Transaction amount modified
 * - game_closed: Game has been closed
 *
 * Usage:
 *   useLiveGameSSE({ joinCode: 'A3B7', enabled: true });
 */

import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from 'react-query';  // React Query v3
import { liveGameKeys } from '../api/liveGame';
import { API_BASE_URL } from '../config/api';

interface LiveGameSSEOptions {
  joinCode: string;
  enabled?: boolean;
}

interface SSEConnectionState {
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  retryCount: number;
  retryDelay: number;
}

// Reconnection configuration
const INITIAL_RETRY_DELAY = 1000;  // 1 second
const MAX_RETRY_DELAY = 30000;     // 30 seconds
const MAX_RETRIES = 10;

export function useLiveGameSSE({ joinCode, enabled = true }: LiveGameSSEOptions) {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [connectionState, setConnectionState] = useState<SSEConnectionState>({
    status: 'disconnected',
    retryCount: 0,
    retryDelay: INITIAL_RETRY_DELAY
  });

  useEffect(() => {
    /**
     * Cleanup SSE connection and retry timeout
     */
    const cleanup = () => {
      // Clear retry timeout
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }

      // Close EventSource
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      setConnectionState({
        status: 'disconnected',
        retryCount: 0,
        retryDelay: INITIAL_RETRY_DELAY
      });
    };

    /**
     * Establish SSE connection with event handlers
     */
    const connect = () => {
      // Prevent duplicate connections
      if (eventSourceRef.current) {
        return;
      }

      const token = localStorage.getItem('auth_token');
      if (!token) return;

      setConnectionState(prev => ({ ...prev, status: 'connecting' }));

      // Create EventSource with token in query param
      // Note: EventSource doesn't support custom headers
      const url = `${API_BASE_URL}/api/live-games/${joinCode}/stream?token=${encodeURIComponent(token)}`;
      const eventSource = new EventSource(url);

      eventSourceRef.current = eventSource;

      // Connection opened
      eventSource.onopen = () => {
        setConnectionState({
          status: 'connected',
          retryCount: 0,
          retryDelay: INITIAL_RETRY_DELAY
        });
      };

      // Connection error
      eventSource.onerror = () => {
        // Close the connection
        eventSource.close();
        eventSourceRef.current = null;

        // Attempt reconnection with exponential backoff
        setConnectionState(prev => {
          const newRetryCount = prev.retryCount + 1;
          const newRetryDelay = Math.min(prev.retryDelay * 2, MAX_RETRY_DELAY);

          if (newRetryCount <= MAX_RETRIES) {
            // Schedule reconnection
            retryTimeoutRef.current = setTimeout(() => {
              connect();
            }, newRetryDelay);

            return {
              status: 'error',
              retryCount: newRetryCount,
              retryDelay: newRetryDelay
            };
          } else {
            return {
              status: 'error',
              retryCount: newRetryCount,
              retryDelay: newRetryDelay
            };
          }
        });
      };

      // Event: participant_joined
      eventSource.addEventListener('participant_joined', (event) => {
        try {
          JSON.parse(event.data);

          // Invalidate participants query to trigger refetch
          queryClient.invalidateQueries(liveGameKeys.participants(joinCode));
        } catch (error) {
          // Silently handle parsing errors
        }
      });

      // Event: transaction_created
      eventSource.addEventListener('transaction_created', (event) => {
        try {
          JSON.parse(event.data);

          // Invalidate pending transactions and participants
          queryClient.invalidateQueries(liveGameKeys.pendingTransactions(joinCode));
          queryClient.invalidateQueries(liveGameKeys.participants(joinCode));
        } catch (error) {
          // Silently handle parsing errors
        }
      });

      // Event: transaction_approved
      eventSource.addEventListener('transaction_approved', (event) => {
        try {
          JSON.parse(event.data);

          // Invalidate all relevant queries
          queryClient.invalidateQueries(liveGameKeys.pendingTransactions(joinCode));
          queryClient.invalidateQueries(liveGameKeys.participants(joinCode));
          queryClient.invalidateQueries(liveGameKeys.summary(joinCode));
        } catch (error) {
          // Silently handle parsing errors
        }
      });

      // Event: transaction_rejected
      eventSource.addEventListener('transaction_rejected', (event) => {
        try {
          JSON.parse(event.data);

          // Invalidate pending transactions
          queryClient.invalidateQueries(liveGameKeys.pendingTransactions(joinCode));
        } catch (error) {
          // Silently handle parsing errors
        }
      });

      // Event: transaction_edited
      eventSource.addEventListener('transaction_edited', (event) => {
        try {
          JSON.parse(event.data);

          // Invalidate all relevant queries
          queryClient.invalidateQueries(liveGameKeys.pendingTransactions(joinCode));
          queryClient.invalidateQueries(liveGameKeys.participants(joinCode));
          queryClient.invalidateQueries(liveGameKeys.summary(joinCode));
        } catch (error) {
          // Silently handle parsing errors
        }
      });

      // Event: game_closed
      eventSource.addEventListener('game_closed', (event) => {
        try {
          JSON.parse(event.data);

          // Don't invalidate queries - let components handle cleanup via redirect
          // Invalidating queries here triggers refetches before components can redirect,
          // causing unnecessary 410/500 errors in console

          // Close SSE connection (game is over)
          cleanup();
        } catch (error) {
          // Silently handle parsing errors
        }
      });
    };

    // Exit early if disabled or no join code
    if (!enabled || !joinCode) {
      cleanup();
      return;
    }

    // Get auth token from localStorage
    const token = localStorage.getItem('auth_token');
    if (!token) {
      return;
    }

    // Establish connection
    connect();

    // Cleanup on unmount or when dependencies change
    return () => {
      cleanup();
    };
    // Note: queryClient is stable (created once at app level)
    // connect() and cleanup() are defined inside useEffect so they always have fresh closures
  }, [joinCode, enabled, queryClient]);

  // Return connection state for debugging/UI feedback (optional)
  return connectionState;
}
