import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAdminSession } from "../../contexts/AdminSessionContext";

export default function LandingPage() {
  const [mode, setMode] = useState<'join' | 'create'>('join');
  const [gameId, setGameId] = useState("");
  const [adminId, setAdminId] = useState("");
  const [gameTitle, setGameTitle] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdGame, setCreatedGame] = useState<any>(null);
  const navigate = useNavigate();
  const { setAdminSession } = useAdminSession();

  const handleJoinGame = (e: React.FormEvent) => {
    e.preventDefault();
    if (gameId) {
      // Store admin session only if admin ID is provided
      if (adminId) {
        setAdminSession(adminId, gameId);
      }
      
      navigate(`/${gameId}`);
    }
  };

  const handleCreateGame = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/games/create', {
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
      console.log('Setting new admin session:', result.public_code, result.admin_code.substring(0, 10) + '...');
      setAdminSession(result.admin_code, result.public_code);

    } catch (err) {
      console.error('Error creating game:', err);
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4">
        <div className="max-w-lg w-full">
          <div className="bg-white rounded-lg border shadow-sm p-8">
            <div className="text-center mb-6">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">Game Created Successfully! 🎉</h1>
              <p className="mt-2 text-gray-600">Your new poker game is ready to use</p>
            </div>
            
            <div className="space-y-4 mb-6">
              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Public Code (Share with players)
                </label>
                <div className="flex items-center space-x-2">
                  <code className="flex-1 bg-white px-3 py-2 border border-gray-300 rounded font-mono text-lg font-bold text-center">
                    {createdGame.public_code}
                  </code>
                  <button
                    onClick={() => navigator.clipboard.writeText(createdGame.public_code)}
                    className="px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Copy
                  </button>
                </div>
              </div>
              
              <div className="bg-yellow-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Admin Code (Keep secret!)
                </label>
                <div className="flex items-center space-x-2">
                  <code className="flex-1 bg-white px-3 py-2 border border-gray-300 rounded font-mono text-sm break-all">
                    {createdGame.admin_code}
                  </code>
                  <button
                    onClick={() => navigator.clipboard.writeText(createdGame.admin_code)}
                    className="px-3 py-2 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700"
                  >
                    Copy
                  </button>
                </div>
                <p className="mt-2 text-xs text-yellow-700">
                  ⚠️ Save this admin code! You'll need it to manage sessions and import data.
                </p>
              </div>
              
              {createdGame.title && (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Game Title
                  </label>
                  <p className="text-gray-900">{createdGame.title}</p>
                </div>
              )}
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={handleGoToGame}
                className="flex-1 px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Go to Game
              </button>
              <button
                onClick={handleCreateAnother}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-900 font-medium rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                Create Another
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-lg border shadow-sm p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">🃏 Poker Analytics</h1>
            <p className="mt-2 text-gray-600">Create a new game or join an existing one</p>
          </div>
          
          {/* Mode Toggle */}
          <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
            <button
              type="button"
              className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                mode === 'join'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              onClick={() => setMode('join')}
            >
              Join Game
            </button>
            <button
              type="button"
              className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                mode === 'create'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              onClick={() => setMode('create')}
            >
              Create Game
            </button>
          </div>
          
          {error && (
            <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400 rounded">
              <div className="text-red-800 font-medium">Error</div>
              <div className="text-red-700">{error}</div>
            </div>
          )}
          
          {mode === 'join' ? (
            <form onSubmit={handleJoinGame} className="space-y-6">
              <div>
                <label htmlFor="gameId" className="block text-sm font-medium text-gray-700 mb-2">
                  Game Code *
                </label>
                <input
                  id="gameId"
                  type="text"
                  value={gameId}
                  onChange={(e) => setGameId(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-center text-lg"
                  placeholder="e.g., C4QROK"
                  required
                />
              </div>
              
              <div>
                <label htmlFor="adminId" className="block text-sm font-medium text-gray-700 mb-2">
                  Admin Code (optional)
                </label>
                <input
                  id="adminId"
                  type="password"
                  value={adminId}
                  onChange={(e) => setAdminId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter admin code for management access"
                />
                <p className="mt-1 text-sm text-gray-500">
                  Required for game management and data ingestion
                </p>
              </div>
              
              <button
                type="submit"
                className="w-full px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Join Game
              </button>
            </form>
          ) : (
            <form onSubmit={handleCreateGame} className="space-y-6">
              <div>
                <label htmlFor="gameTitle" className="block text-sm font-medium text-gray-700 mb-2">
                  Game Title (optional)
                </label>
                <input
                  id="gameTitle"
                  type="text"
                  value={gameTitle}
                  onChange={(e) => setGameTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  placeholder="e.g., Thursday Night Home Game"
                  maxLength={100}
                />
                <p className="mt-1 text-sm text-gray-500">
                  Give your game a memorable name
                </p>
              </div>
              
              <button
                type="submit"
                disabled={isLoading}
                className="w-full px-4 py-2 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Creating Game...' : 'Create New Game'}
              </button>
            </form>
          )}
          
          <div className="mt-8 p-4 bg-blue-50 border-l-4 border-blue-400 rounded">
            <h3 className="font-medium text-blue-800 mb-2">Features</h3>
            <ul className="text-blue-700 text-sm space-y-1">
              <li>• View player statistics and game summaries</li>
              <li>• Import PokerNow sessions automatically</li>
              <li>• Enter live game results manually</li>
              <li>• Track player performance over time</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}