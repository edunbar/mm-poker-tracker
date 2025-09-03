import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import AdminSessionStatus from '../../../components/AdminSessionStatus';

interface SessionPlayerSummary {
  session_id: string;
  player_id: string;
  player_name: string;
  session_external_id: string;
  session_started_at: string | null;
  session_ended_at: string | null;
  buy_in_sum: number;
  cash_out_sum: number;
  in_game: number;
  net: number;
  names: string[];
  game_number: number;
}

interface EditingRow {
  session_id: string;
  player_id: string;
  buy_in_sum: number;
  cash_out_sum: number;
  in_game: number;
  net: number;
  names: string[];
}

interface SessionGroup {
  session_id: string;
  session_external_id: string;
  session_started_at: string | null;
  game_number: number;
  players: SessionPlayerSummary[];
}

export default function GameLedgerPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const { adminCode: sessionAdminCode, hasAdminSession } = useAdminSession();
  const [summaries, setSummaries] = useState<SessionPlayerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingRow, setEditingRow] = useState<EditingRow | null>(null);
  const [manualAdminCode, setManualAdminCode] = useState('');
  const [showAdminInput, setShowAdminInput] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<{sessionId: string, playerId: string} | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{sessionId: string, playerId: string, playerName: string} | null>(null);
  const [showSessionDeleteModal, setShowSessionDeleteModal] = useState(false);
  const [sessionDeleteTarget, setSessionDeleteTarget] = useState<{sessionId: string, gameNumber: number, playerCount: number} | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  // Use session admin code if available, otherwise manual input
  const effectiveAdminCode = sessionAdminCode || manualAdminCode;

  useEffect(() => {
    if (publicCode) {
      fetchLedgerData();
    }
  }, [publicCode]);

  useEffect(() => {
    // Reserve space for scrollbar to prevent layout shift
    document.documentElement.style.overflowY = 'scroll';
    
    return () => {
      // Reset on unmount
      document.documentElement.style.overflowY = 'auto';
    };
  }, []);

  const fetchLedgerData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/ledger`);
      setSummaries(response.data.summaries || []);
    } catch (error) {
      console.error('Error fetching ledger data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (summary: SessionPlayerSummary) => {
    setEditingRow({
      session_id: summary.session_id,
      player_id: summary.player_id,
      buy_in_sum: summary.buy_in_sum,
      cash_out_sum: summary.cash_out_sum,
      in_game: summary.in_game,
      net: summary.net,
      names: summary.names,
    });
    // Only show admin input if no admin session is active
    if (!hasAdminSession) {
      setShowAdminInput(true);
    }
  };

  const handleSave = async () => {
    if (!editingRow || !effectiveAdminCode) return;

    try {
      const updateData = {
        buy_in_sum: editingRow.buy_in_sum,
        cash_out_sum: editingRow.cash_out_sum,
        in_game: editingRow.in_game,
        net: editingRow.net,
        names: editingRow.names,
      };

      await axios.put(
        `http://localhost:8000/api/games/${publicCode}/ledger/${editingRow.session_id}/${editingRow.player_id}`,
        updateData,
        {
          headers: {
            'X-Admin-Code': effectiveAdminCode,
            'Content-Type': 'application/json',
          },
        }
      );

      setEditingRow(null);
      setShowAdminInput(false);
      setManualAdminCode('');
      fetchLedgerData();
    } catch (error) {
      console.error('Error updating record:', error);
      setErrorMessage('Failed to update record. Please check your admin code.');
      setTimeout(() => setErrorMessage(null), 5000);
    }
  };

  const handleDelete = async (sessionId: string, playerId: string, playerName: string) => {
    if (!effectiveAdminCode) {
      // Set pending delete and show admin input
      setPendingDelete({ sessionId, playerId });
      setShowAdminInput(true);
      return;
    }

    // Show professional delete confirmation modal
    setDeleteTarget({ sessionId, playerId, playerName });
    setShowDeleteModal(true);
  };

  const performDelete = async (sessionId: string, playerId: string) => {
    try {
      await axios.delete(
        `http://localhost:8000/api/games/${publicCode}/ledger/${sessionId}/${playerId}`,
        {
          headers: {
            'X-Admin-Code': effectiveAdminCode,
          },
        }
      );

      setManualAdminCode('');
      setShowAdminInput(false);
      setPendingDelete(null);
      fetchLedgerData();
    } catch (error) {
      console.error('Error deleting record:', error);
      setErrorMessage('Failed to delete record. Please check your admin code.');
      setTimeout(() => setErrorMessage(null), 5000);
    }
  };

  const handleSessionDelete = async (sessionId: string, gameNumber: number, playerCount: number) => {
    if (!effectiveAdminCode) {
      // Show admin input if needed
      setShowAdminInput(true);
      return;
    }

    // Show professional session delete confirmation modal
    setSessionDeleteTarget({ sessionId, gameNumber, playerCount });
    setShowSessionDeleteModal(true);
  };

  const performSessionDelete = async (sessionId: string) => {
    try {
      await axios.delete(
        `http://localhost:8000/api/games/${publicCode}/sessions/${sessionId}`,
        {
          headers: {
            'X-Admin-Code': effectiveAdminCode,
          },
        }
      );

      setManualAdminCode('');
      setShowAdminInput(false);
      fetchLedgerData();
    } catch (error) {
      console.error('Error deleting session:', error);
      setErrorMessage('Failed to delete session. Please check your admin code.');
      setTimeout(() => setErrorMessage(null), 5000);
    }
  };

  const handleCancel = () => {
    setEditingRow(null);
    setShowAdminInput(false);
    setManualAdminCode('');
    setPendingDelete(null);
  };

  const formatCurrency = (amount: number) => {
    return (amount / 100).toFixed(2);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  // Group summaries by session
  const groupedSessions: SessionGroup[] = summaries.reduce((groups: SessionGroup[], summary) => {
    const existingGroup = groups.find(g => g.session_id === summary.session_id);
    if (existingGroup) {
      existingGroup.players.push(summary);
    } else {
      groups.push({
        session_id: summary.session_id,
        session_external_id: summary.session_external_id,
        session_started_at: summary.session_started_at,
        game_number: summary.game_number,
        players: [summary]
      });
    }
    return groups;
  }, []);

  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());

  // Default expand all sessions when data loads
  useEffect(() => {
    if (!loading && summaries.length > 0) {
      const allSessionIds = new Set(summaries.map(s => s.session_id));
      setExpandedSessions(allSessionIds);
    }
  }, [loading, summaries]);

  const toggleSession = (sessionId: string) => {
    const newExpanded = new Set(expandedSessions);
    if (newExpanded.has(sessionId)) {
      newExpanded.delete(sessionId);
    } else {
      newExpanded.add(sessionId);
    }
    setExpandedSessions(newExpanded);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <AdminSessionStatus className="mb-4" compact />
        
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Game Ledger</h1>
            <p className="mt-2 text-gray-600">
              Session and player data for game <span className="font-mono bg-gray-100 px-2 py-1 rounded">{publicCode}</span>
            </p>
          </div>
          <button
            onClick={fetchLedgerData}
            className="px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Refresh
          </button>
        </div>

      {showAdminInput && (
        <div className="bg-white rounded-lg border shadow-sm p-4 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Admin Code:
          </label>
          <div className="flex gap-2">
            <input
              type="password"
              value={manualAdminCode}
              onChange={(e) => setManualAdminCode(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter admin code"
            />
            {editingRow ? (
              <>
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-green-600 text-white font-medium rounded-md hover:bg-green-700"
                >
                  Save
                </button>
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 bg-gray-500 text-white font-medium rounded-md hover:bg-gray-600"
                >
                  Cancel
                </button>
              </>
            ) : pendingDelete ? (
              <>
                <button
                  onClick={() => {
                    // Find the player name for the pending delete
                    const summary = summaries.find(s => 
                      s.session_id === pendingDelete.sessionId && 
                      s.player_id === pendingDelete.playerId
                    );
                    setDeleteTarget({ 
                      sessionId: pendingDelete.sessionId, 
                      playerId: pendingDelete.playerId, 
                      playerName: summary?.player_name || 'Unknown Player' 
                    });
                    setShowDeleteModal(true);
                  }}
                  className="px-4 py-2 bg-red-600 text-white font-medium rounded-md hover:bg-red-700"
                >
                  Delete
                </button>
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 bg-gray-500 text-white font-medium rounded-md hover:bg-gray-600"
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={handleCancel}
                className="px-4 py-2 bg-gray-500 text-white font-medium rounded-md hover:bg-gray-600"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full table-fixed w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-8 px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                
              </th>
              <th className="w-32 px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Session/Player
              </th>
              <th className="w-32 px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Session Date
              </th>
              <th className="w-24 px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Buy In
              </th>
              <th className="w-24 px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cash Out
              </th>
              <th className="w-24 px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Net
              </th>
              <th className="w-16 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Names
              </th>
              <th className="w-20 px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Game Number
              </th>
              {hasAdminSession && (
                <th className="w-32 px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              // Create multiple skeleton rows to maintain table height
              Array.from({ length: 10 }).map((_, index) => (
                <tr key={`loading-${index}`} className="animate-pulse">
                  <td className="w-8 px-3 py-4 whitespace-nowrap">
                    <div className="h-5 bg-gray-200 rounded w-4"></div>
                  </td>
                  <td className="w-32 px-6 py-4 whitespace-nowrap">
                    <div className="h-5 bg-gray-200 rounded w-28"></div>
                  </td>
                  <td className="w-48 px-6 py-4 whitespace-nowrap">
                    <div className="h-5 bg-gray-200 rounded w-36"></div>
                  </td>
                  <td className="w-24 px-6 py-4 whitespace-nowrap text-right">
                    <div className="h-5 bg-gray-200 rounded w-16 ml-auto"></div>
                  </td>
                  <td className="w-24 px-6 py-4 whitespace-nowrap text-right">
                    <div className="h-5 bg-gray-200 rounded w-16 ml-auto"></div>
                  </td>
                  <td className="w-24 px-6 py-4 whitespace-nowrap text-right">
                    <div className="h-5 bg-gray-200 rounded w-16 ml-auto"></div>
                  </td>
                  <td className="w-16 px-2 py-4">
                    <div className="h-5 bg-gray-200 rounded w-12 truncate"></div>
                  </td>
                  <td className="w-20 px-6 py-4 whitespace-nowrap text-center">
                    <div className="h-5 bg-gray-200 rounded w-6 mx-auto"></div>
                  </td>
                  {hasAdminSession && (
                    <td className="w-32 px-6 py-4 whitespace-nowrap text-center">
                      <div className="flex gap-2 justify-center">
                        <div className="h-5 bg-gray-200 rounded w-10"></div>
                        <div className="h-5 bg-gray-200 rounded w-12"></div>
                      </div>
                    </td>
                  )}
                </tr>
              ))
            ) : groupedSessions.map((sessionGroup) => (
              <>
                {/* Session Header Row */}
                <tr key={`session-${sessionGroup.session_id}`} className="bg-blue-50 hover:bg-blue-100 border-l-4 border-blue-500">
                  <td className="px-3 py-4 whitespace-nowrap w-8">
                    <button
                      onClick={() => toggleSession(sessionGroup.session_id)}
                      className="flex items-center justify-center w-6 h-6 bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                      {expandedSessions.has(sessionGroup.session_id) ? '−' : '+'}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-blue-900 w-32">
                    Game #{sessionGroup.game_number} ({sessionGroup.players.length} players)
                  </td>
                  <td className="px-6 py-4 text-sm text-blue-800 w-32 max-w-32 break-words">
                    {formatDate(sessionGroup.session_started_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-800 text-right w-24">
                    ${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.buy_in_sum, 0))}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-800 text-right w-24">
                    ${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.cash_out_sum + p.in_game, 0))}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right w-24">
                    <span className={sessionGroup.players.reduce((sum, p) => sum + p.net, 0) >= 0 ? 'text-green-600' : 'text-red-600'}>
                      ${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.net, 0))}
                    </span>
                  </td>
                  <td className="px-2 py-4 text-sm text-blue-800 w-16 max-w-16 overflow-hidden">
                    <div className="truncate text-xs w-full" title={sessionGroup.session_external_id || 'N/A'}>
                      {sessionGroup.session_external_id || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-800 text-center w-20">
                    {sessionGroup.game_number}
                  </td>
                  {hasAdminSession && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium w-32">
                      <button
                        onClick={() => handleSessionDelete(sessionGroup.session_id, sessionGroup.game_number, sessionGroup.players.length)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Delete Session
                      </button>
                    </td>
                  )}
                </tr>
                
                {/* Player Rows (expandable) */}
                {expandedSessions.has(sessionGroup.session_id) && sessionGroup.players.map((summary) => (
                  <tr key={`${summary.session_id}-${summary.player_id}`} className="hover:bg-gray-50 bg-gray-25">
                    <td className="px-3 py-4"></td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 pl-12">
                      {summary.player_name}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      —
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="number"
                          value={editingRow.buy_in_sum}
                          onChange={(e) => setEditingRow({ ...editingRow, buy_in_sum: parseInt(e.target.value) || 0 })}
                          className="w-16 px-1 py-1 border rounded text-xs"
                        />
                      ) : (
                        `$${formatCurrency(summary.buy_in_sum)}`
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="number"
                          value={editingRow.cash_out_sum + editingRow.in_game}
                          onChange={(e) => {
                            const totalValue = parseInt(e.target.value) || 0;
                            setEditingRow({ 
                              ...editingRow, 
                              cash_out_sum: totalValue,
                              in_game: 0
                            });
                          }}
                          className="w-16 px-1 py-1 border rounded text-xs"
                          title="Total cash out + in game"
                        />
                      ) : (
                        `$${formatCurrency(summary.cash_out_sum + summary.in_game)}`
                      )}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium text-right ${summary.net >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="number"
                          value={editingRow.net}
                          onChange={(e) => setEditingRow({ ...editingRow, net: parseInt(e.target.value) || 0 })}
                          className="w-16 px-1 py-1 border rounded text-xs"
                        />
                      ) : (
                        `$${formatCurrency(summary.net)}`
                      )}
                    </td>
                    <td className="px-2 py-4 text-sm text-gray-900 w-16 max-w-16 overflow-hidden">
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="text"
                          value={editingRow.names.join(', ')}
                          onChange={(e) => setEditingRow({ ...editingRow, names: e.target.value.split(', ') })}
                          className="w-full px-1 py-1 border rounded text-xs"
                        />
                      ) : (
                        <div className="truncate text-xs w-full" title={summary.names.join(', ')}>
                          {summary.names.join(', ')}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      —
                    </td>
                    {hasAdminSession && (
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex gap-2">
                          {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                            <>
                              <button
                                onClick={handleSave}
                                className="text-green-600 hover:text-green-900"
                              >
                                Save
                              </button>
                              <button
                                onClick={handleCancel}
                                className="text-gray-600 hover:text-gray-900"
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => handleEdit(summary)}
                                className="text-blue-600 hover:text-blue-900"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDelete(summary.session_id, summary.player_id, summary.player_name)}
                                className="text-red-600 hover:text-red-900"
                              >
                                Delete
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </>
            ))}
          </tbody>
        </table>
        </div>
      </div>

      {!loading && summaries.length === 0 && (
        <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
          <p className="text-gray-500">No game ledger entries found.</p>
        </div>
      )}

      {/* Error Message Display */}
      {errorMessage && (
        <div className="fixed top-4 right-4 bg-red-50 border-l-4 border-red-400 rounded px-4 py-3 shadow-lg z-50">
          <div className="flex items-center">
            <svg className="w-4 h-4 mr-2 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-red-800">{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && deleteTarget && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-40">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-xl font-semibold text-gray-900">Confirm Deletion</h3>
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteTarget(null);
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <span className="sr-only">Close</span>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="pt-4 pb-6">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h4 className="text-lg font-medium text-gray-900 mb-2">Delete Player Record</h4>
                  <p className="text-sm text-gray-600 mb-4">
                    Are you sure you want to delete the record for <strong>{deleteTarget.playerName}</strong>? 
                    This action cannot be undone and will permanently remove this player's data from the session.
                  </p>
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <p className="text-sm text-red-800">
                      <strong>Warning:</strong> This will delete the player record from both the database and Google Sheets.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteTarget(null);
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await performDelete(deleteTarget.sessionId, deleteTarget.playerId);
                  setShowDeleteModal(false);
                  setDeleteTarget(null);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Delete Record
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Session Delete Confirmation Modal */}
      {showSessionDeleteModal && sessionDeleteTarget && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-40">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-xl font-semibold text-gray-900">Confirm Session Deletion</h3>
              <button
                onClick={() => {
                  setShowSessionDeleteModal(false);
                  setSessionDeleteTarget(null);
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <span className="sr-only">Close</span>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="pt-4 pb-6">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h4 className="text-lg font-medium text-gray-900 mb-2">Delete Entire Session</h4>
                  <p className="text-sm text-gray-600 mb-4">
                    Are you sure you want to delete <strong>Game #{sessionDeleteTarget.gameNumber}</strong> and all associated player records? 
                    This will permanently remove <strong>{sessionDeleteTarget.playerCount} player record(s)</strong> from the session.
                  </p>
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <p className="text-sm text-red-800">
                      <strong>Warning:</strong> This action cannot be undone and will delete the entire session from both the database and Google Sheets.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                onClick={() => {
                  setShowSessionDeleteModal(false);
                  setSessionDeleteTarget(null);
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await performSessionDelete(sessionDeleteTarget.sessionId);
                  setShowSessionDeleteModal(false);
                  setSessionDeleteTarget(null);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Delete Session
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}