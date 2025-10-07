import axios from 'axios';
import React from 'react';
import { useQuery } from 'react-query';
import { API_BASE_URL } from '../config/api';
import { GameNotFoundPage } from '../pages/GameNotFoundPage';

interface GamePageWrapperProps {
  publicCode: string;
  children: React.ReactNode;
}

/**
 * Wrapper component that validates a game exists before rendering child components.
 * Shows loading state during validation, GameNotFoundPage if game doesn't exist,
 * or renders children if game is valid.
 */
export const GamePageWrapper: React.FC<GamePageWrapperProps> = ({ publicCode, children }) => {
  // Validate game exists by calling the summary endpoint
  const { isLoading, error } = useQuery(
    ['gameValidation', publicCode],
    async () => {
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/summary`);
      return response.data;
    },
    {
      retry: false, // Don't retry on 404
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    }
  );

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading game...</p>
        </div>
      </div>
    );
  }

  // Show game not found page if 404 error
  if (error && axios.isAxiosError(error) && error.response?.status === 404) {
    return <GameNotFoundPage />;
  }

  // Show generic error for other errors
  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="max-w-md w-full mx-auto text-center px-4">
          <p className="text-destructive mb-4">Failed to load game</p>
          <p className="text-muted-foreground text-sm">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
        </div>
      </div>
    );
  }

  // Game is valid, render children
  return <>{children}</>;
};
