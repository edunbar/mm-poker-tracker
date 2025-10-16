import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../../config/api";
import { useAdminSession } from "../../contexts/AdminSessionContext";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../contexts/ToastContext";
import { Button } from "../../shared/ui/button";
import { FormField, FormLabel, FormMessage } from "../../shared/ui/form-field";
import { Input } from "../../shared/ui/input";
import { Heading, Text, Code } from "../../shared/ui/typography";

export default function LandingPage() {
  const [mode, setMode] = useState<'join' | 'create'>('join');
  const [gameId, setGameId] = useState("");
  const [adminId, setAdminId] = useState("");
  const [gameTitle, setGameTitle] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdGame, setCreatedGame] = useState<{
    public_code: string;
    admin_code: string;
    title?: string;
  } | null>(null);
  const navigate = useNavigate();
  const { setAdminSession } = useAdminSession();
  const { showError } = useToast();
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();

  // Show loading spinner while checking authentication
  if (isAuthLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto" />
          <Text variant="body" color="muted" className="mt-4">
            Loading...
          </Text>
        </div>
      </div>
    );
  }

  // Redirect authenticated users to their games dashboard
  if (isAuthenticated) {
    return <Navigate to="/my-games" replace />;
  }

  const handleJoinGame = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gameId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Validate game exists by calling the summary endpoint
      const response = await fetch(`${API_BASE_URL}/api/games/${gameId}/summary`);

      if (response.status === 404) {
        showError("Game Not Found", "Please check your game code and try again");
        return;
      }

      if (!response.ok) {
        throw new Error("Failed to validate game");
      }

      // Game exists, proceed with navigation
      // Store admin session only if admin ID is provided
      if (adminId) {
        setAdminSession(adminId, gameId);
      }

      navigate(`/${gameId}`);
    } catch (err) {
      showError("Error", "An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateGame = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/games/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: gameTitle.trim() || undefined
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to create game');
      }

      setCreatedGame(result);
      // Clear any existing session and set new admin session
      setAdminSession(result.admin_code, result.public_code);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoToGame = () => {
    if (createdGame) {
      // Set admin session and navigate to the new game
      setAdminSession(createdGame.admin_code, createdGame.public_code);
      navigate(`/${createdGame.public_code}`);
    }
  };

  const handleCreateAnother = () => {
    setCreatedGame(null);
    setGameTitle('');
    setError(null);
  };

  // Success modal for game creation
  if (createdGame) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center py-12 px-4">
        <div className="max-w-lg w-full">
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-8">
            <div className="text-center mb-6">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-success/20 mb-4">
                <svg className="h-6 w-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <Heading variant="h2">Game Created Successfully! 🎉</Heading>
              <Text variant="bodyLarge" color="muted" className="mt-2">Your new poker game is ready to use</Text>
            </div>
            
            <div className="space-y-4 mb-6">
              <div className="bg-muted p-4 rounded-lg">
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  Public Code (Share with players)
                </Text>
                <div className="flex items-center space-x-2">
                  <Code className="flex-1 bg-background px-3 py-2 border border-input rounded text-lg font-bold text-center">
                    {createdGame.public_code}
                  </Code>
                  <Button
                    onClick={() => navigator.clipboard.writeText(createdGame.public_code)}
                    size="sm"
                  >
                    Copy
                  </Button>
                </div>
              </div>

              <div className="bg-warning/20 p-4 rounded-lg">
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  Admin Code (Keep secret!)
                </Text>
                <div className="flex items-center space-x-2">
                  <Code className="flex-1 bg-background px-3 py-2 border border-input rounded text-sm break-all">
                    {createdGame.admin_code}
                  </Code>
                  <Button
                    onClick={() => navigator.clipboard.writeText(createdGame.admin_code)}
                    size="sm"
                  >
                    Copy
                  </Button>
                </div>
                <Text variant="caption" color="warning" className="mt-2">
                  ⚠️ Save this admin code! You'll need it to manage sessions and import data.
                </Text>
              </div>

              {createdGame.title && (
                <div className="bg-muted p-4 rounded-lg">
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                    Game Title
                  </Text>
                  <Text>{createdGame.title}</Text>
                </div>
              )}
            </div>
            
            <div className="flex space-x-3">
              <Button
                onClick={handleGoToGame}
                className="flex-1"
              >
                Go to Game
              </Button>
              <Button
                onClick={handleCreateAnother}
                variant="outline"
                className="flex-1"
              >
                Create Another
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center py-12 px-4">
      <div className="max-w-md w-full">
        <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-8">
          <div className="text-center mb-8">
            <Heading variant="h1">🃏 HomeGame</Heading>
            <Text variant="bodyLarge" color="muted" className="mt-2">Create a new game or join an existing one</Text>
          </div>
          
          {/* Mode Toggle */}
          <div className="flex mb-6 bg-muted rounded-lg p-1">
            <Button
              type="button"
              variant={mode === 'join' ? 'secondary' : 'ghost'}
              className="flex-1"
              onClick={() => setMode('join')}
            >
              Join Game
            </Button>
            <Button
              type="button"
              variant={mode === 'create' ? 'secondary' : 'ghost'}
              className="flex-1"
              onClick={() => setMode('create')}
            >
              Create Game
            </Button>
          </div>
          
          {error && (
            <div className="mb-6 p-4 bg-destructive/10 border-l-4 border-destructive rounded">
              <Text weight="medium" color="destructive">Error</Text>
              <Text color="destructive" className="opacity-80">{error}</Text>
            </div>
          )}
          
          {mode === 'join' ? (
            <form onSubmit={handleJoinGame} className="space-y-6">
              <FormField>
                <FormLabel htmlFor="gameId" required>
                  Game Code
                </FormLabel>
                <Input
                  id="gameId"
                  type="text"
                  value={gameId}
                  onChange={(e) => setGameId(e.target.value.toUpperCase())}
                  placeholder="e.g., C4QROK"
                  className="font-mono text-center text-lg"
                  required
                />
              </FormField>
              
              <FormField>
                <FormLabel htmlFor="adminId">
                  Admin Code (optional)
                </FormLabel>
                <Input
                  id="adminId"
                  type="password"
                  value={adminId}
                  onChange={(e) => setAdminId(e.target.value)}
                  placeholder="Enter admin code for management access"
                />
                <FormMessage>
                  Required for game management and data ingestion
                </FormMessage>
              </FormField>
              
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full"
              >
                {isLoading ? 'Validating Game...' : 'Join Game'}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleCreateGame} className="space-y-6">
              <FormField>
                <FormLabel htmlFor="gameTitle">
                  Game Title (optional)
                </FormLabel>
                <Input
                  id="gameTitle"
                  type="text"
                  value={gameTitle}
                  onChange={(e) => setGameTitle(e.target.value)}
                  placeholder="e.g., Thursday Night Home Game"
                  maxLength={100}
                />
                <FormMessage>
                  Give your game a memorable name
                </FormMessage>
              </FormField>
              
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full"
              >
                {isLoading ? 'Creating Game...' : 'Create New Game'}
              </Button>
            </form>
          )}
          
          <div className="mt-8 p-4 bg-info/10 border-l-4 border-info rounded">
            <Heading variant="h6" color="primary" className="mb-2">Why Create an Account?</Heading>
            <ul className="space-y-1">
              <Text variant="bodySmall" color="primary" className="opacity-80" as="li">• Create unlimited games with your account</Text>
              <Text variant="bodySmall" color="primary" className="opacity-80" as="li">• Access all your games from any device</Text>
              <Text variant="bodySmall" color="primary" className="opacity-80" as="li">• Never lose admin codes again</Text>
              <Text variant="bodySmall" color="primary" className="opacity-80" as="li">• Track player stats across all sessions</Text>
              <Text variant="bodySmall" color="primary" className="opacity-80" as="li">• Import PokerNow data automatically</Text>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}