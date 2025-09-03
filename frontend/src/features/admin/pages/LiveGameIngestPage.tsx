import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import LiveGameForm from '../components/LiveGameForm';
import { useAdminSession } from '../../../contexts/AdminSessionContext';

interface LiveGameData {
  sessionName: string;
  players: Array<{
    name: string;
    buy_in: number;
    cash_out: number;
  }>;
  date?: string;
  gameNumber?: number;
}

export default function LiveGameIngestPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const navigate = useNavigate();
  const { adminCode } = useAdminSession();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (data: LiveGameData) => {
    if (!publicCode) {
      setError('Public code is missing');
      return;
    }

    if (!adminCode) {
      setError('Admin code is missing. Please log in.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('http://localhost:8000/api/games/upload_live', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Code': adminCode,
        },
        body: JSON.stringify({
          public_code: publicCode,
          session_name: data.sessionName,
          players: data.players,
          ...(data.date && { date: data.date }),
          ...(data.gameNumber && { gameNumber: data.gameNumber })
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to submit live game');
      }

      setSuccess(`Live game "${data.sessionName}" submitted successfully! Game #${result.game_number || 'auto-assigned'}`);
      
      // Optional: Navigate to summary page after success
      setTimeout(() => {
        navigate(`/summary/${publicCode}`);
      }, 2000);

    } catch (err) {
      console.error('Error submitting live game:', err);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Submit Live Game Results</h1>
          <p className="mt-2 text-gray-600">
            Enter the results from your live poker game for game <span className="font-mono bg-gray-100 px-2 py-1 rounded">{publicCode}</span>
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400 rounded">
            <div className="text-red-800 font-medium">Error</div>
            <div className="text-red-700">{error}</div>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border-l-4 border-green-400 rounded">
            <div className="text-green-800 font-medium">Success!</div>
            <div className="text-green-700">{success}</div>
            <div className="text-green-600 text-sm mt-1">Redirecting to game summary...</div>
          </div>
        )}

        <LiveGameForm onSubmit={handleSubmit} isLoading={isLoading} />

        <div className="mt-8 p-4 bg-blue-50 border-l-4 border-blue-400 rounded">
          <h3 className="font-medium text-blue-800 mb-2">Tips for Live Game Entry</h3>
          <ul className="text-blue-700 text-sm space-y-1">
            <li>• Enter buy-ins and cash-outs in dollars (e.g., 100.00)</li>
            <li>• The balance should equal 0 if all money is accounted for</li>
            <li>• Player names should match previous sessions for consistent tracking</li>
            <li>• Game number will be auto-assigned if left empty</li>
          </ul>
        </div>
      </div>
    </div>
  );
}