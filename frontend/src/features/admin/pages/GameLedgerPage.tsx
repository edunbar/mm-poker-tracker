import axios from 'axios';
import { Edit, MoreVertical, Plus, Save, Trash2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';
import { Pagination, usePagination } from '../../../shared/ui/pagination';

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
  const { title: _title } = useGameTitle(publicCode || '');
  const [summaries, setSummaries] = useState<SessionPlayerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingRow, setEditingRow] = useState<EditingRow | null>(null);
  const [manualAdminCode, setManualAdminCode] = useState('');
  const [showAdminInput, setShowAdminInput] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<{sessionId: string, playerId: string} | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{sessionId: string, playerId: string, playerName: string} | null>(null);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [showSessionDeleteModal, setShowSessionDeleteModal] = useState(false);
  const [sessionDeleteTarget, setSessionDeleteTarget] = useState<{sessionId: string, gameNumber: number, playerCount: number} | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showAddRowModal, setShowAddRowModal] = useState(false);
  const [newRowData, setNewRowData] = useState({
    sessionId: '',
    playerName: '',
    buyInSum: '',
    cashOutSum: '',
    inGame: ''
  });
  
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
    document.documentElement.style.overscrollBehavior = 'none';
    
    return () => {
      // Reset on unmount
      document.documentElement.style.overflowY = 'auto';
      document.documentElement.style.overscrollBehavior = 'auto';
    };
  }, []);

  const fetchLedgerData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/ledger`);
      setSummaries(response.data.summaries || []);
    } catch (error) {
    } finally {
      setLoading(false);
    }
  };

  const handleAddRow = async () => {
    if (!effectiveAdminCode) {
      setErrorMessage('Admin code is required to add a row');
      return;
    }

    if (!newRowData.sessionId || !newRowData.playerName || !newRowData.buyInSum) {
      setErrorMessage('Session ID, Player Name, and Buy In are required');
      return;
    }

    try {
      const buyIn = parseFloat(newRowData.buyInSum) * 100; // Convert to cents
      const cashOut = parseFloat(newRowData.cashOutSum || '0') * 100;
      const inGame = parseFloat(newRowData.inGame || '0') * 100;
      
      // Create a simple POST request - we'll handle this with existing endpoint for now
      await axios.put(`http://localhost:8000/api/games/${publicCode}/ledger/manual/new`, {
        session_external_id: newRowData.sessionId,
        player_name: newRowData.playerName,
        buy_in_sum: buyIn,
        cash_out_sum: cashOut,
        in_game: inGame
      }, {
        headers: {
          'X-Admin-Code': effectiveAdminCode,
          'Content-Type': 'application/json'
        }
      });

      // Reset form and close modal
      setNewRowData({
        sessionId: '',
        playerName: '',
        buyInSum: '',
        cashOutSum: '',
        inGame: ''
      });
      setShowAddRowModal(false);
      setErrorMessage(null);
      
      // Refresh data
      fetchLedgerData();
    } catch (error: any) {
      setErrorMessage(
        error.response?.data?.error || 
        'Failed to add row. Please try again.'
      );
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
    return new Date(dateString).toLocaleDateString();
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

  // Pagination logic - sort sessions by game number (most recent first)
  const sortedSessions = [...groupedSessions].sort((a, b) => b.game_number - a.game_number);
  const {
    currentPage,
    totalPages,
    startIndex,
    endIndex,
    goToPage,
    itemsPerPage
  } = usePagination(sortedSessions.length, 10); // 10 sessions per page
  
  const paginatedSessions = sortedSessions.slice(startIndex, endIndex);

  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());

  // Default expand all sessions when data loads
  useEffect(() => {
    if (!loading && summaries.length > 0) {
      const allSessionIds = new Set(summaries.map(s => s.session_id));
      setExpandedSessions(allSessionIds);
    }
  }, [loading, summaries]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('[data-dropdown]')) {
        setActiveDropdown(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Game Ledger</h1>
            <p className="mt-2 text-muted-foreground">
              Session and player data
            </p>
          </div>
          <button
            onClick={fetchLedgerData}
            className="px-4 py-2 bg-primary text-primary-foreground font-medium rounded-2xl hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            Refresh
          </button>
        </div>

      {showAdminInput && (
        <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-4 mb-6">
          <label className="block text-sm font-medium text-foreground mb-2">
            Admin Code:
          </label>
          <div className="flex gap-2">
            <input
              type="password"
              value={manualAdminCode}
              onChange={(e) => setManualAdminCode(e.target.value)}
              className="flex-1 px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring bg-background text-foreground"
              placeholder="Enter admin code"
            />
            {editingRow ? (
              <>
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-black text-white font-medium rounded-2xl hover:opacity-90"
                >
                  Save
                </button>
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 border border-input bg-background text-muted-foreground font-medium rounded-2xl hover:bg-accent"
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
                  className="px-4 py-2 bg-destructive text-destructive-foreground font-medium rounded-2xl hover:bg-destructive/90"
                >
                  Delete
                </button>
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 border border-input bg-background text-muted-foreground font-medium rounded-2xl hover:bg-accent"
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={handleCancel}
                className="px-4 py-2 border border-input bg-transparent text-foreground font-medium rounded-2xl hover:bg-accent"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      )}

      <div className="overflow-auto rounded-xl border border-border bg-card">
          <table className="min-w-full">
          <thead className="bg-card border-b border-border">
            <tr>
              <th className="px-4 py-4 text-left text-sm font-semibold text-muted-foreground" />
              <th className="px-6 py-4 text-left text-sm font-semibold text-muted-foreground">
                Session/Player
              </th>
              <th className="px-6 py-4 text-right text-sm font-semibold text-muted-foreground">
                Buy In
              </th>
              <th className="px-6 py-4 text-right text-sm font-semibold text-muted-foreground">
                Cash Out
              </th>
              <th className="px-6 py-4 text-right text-sm font-semibold text-muted-foreground">
                Net
              </th>
              <th className="px-6 py-4 text-left text-sm font-semibold text-muted-foreground">
                Names
              </th>
              {hasAdminSession && (
                <th className="px-6 py-4 text-center text-sm font-semibold text-muted-foreground">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-card">
            {loading ? (
              // Create multiple skeleton rows to maintain table height
              Array.from({ length: 10 }).map((_, index) => (
                <tr key={`loading-${index}`} className="animate-pulse border-b border-border">
                  <td className="px-4 py-4">
                    <div className="h-5 bg-muted rounded w-4" />
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-5 bg-muted rounded w-32" />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="h-5 bg-muted rounded w-20 ml-auto" />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="h-5 bg-muted rounded w-20 ml-auto" />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="h-5 bg-muted rounded w-20 ml-auto" />
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-5 bg-muted rounded w-24" />
                  </td>
                  {hasAdminSession && (
                    <td className="px-6 py-4 text-center">
                      <div className="flex gap-2 justify-center">
                        <div className="h-5 bg-muted rounded w-12" />
                      </div>
                    </td>
                  )}
                </tr>
              ))
            ) : paginatedSessions.map((sessionGroup) => (
              <>
                {/* Session Header Row */}
                <tr key={`session-${sessionGroup.session_id}`} className="bg-accent hover:bg-accent/80 border-l-4 border-primary border-b border-border">
                  <td className="px-4 py-4">
                    <button
                      onClick={() => toggleSession(sessionGroup.session_id)}
                      className="flex items-center justify-center w-6 h-6 bg-primary text-primary-foreground rounded-full hover:bg-primary/90"
                    >
                      {expandedSessions.has(sessionGroup.session_id) ? '−' : '+'}
                    </button>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-semibold text-accent-foreground">Game #{sessionGroup.game_number}</div>
                    <div className="text-xs text-accent-foreground opacity-80">
                      {formatDate(sessionGroup.session_started_at)} • ({sessionGroup.players.length} players)
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-accent-foreground text-right font-medium">
                    ${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.buy_in_sum, 0))}
                  </td>
                  <td className="px-6 py-4 text-sm text-accent-foreground text-right font-medium">
                    ${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.cash_out_sum + p.in_game, 0))}
                  </td>
                  <td className="px-6 py-4 text-sm font-semibold text-right">
                    <span className={sessionGroup.players.reduce((sum, p) => sum + p.net, 0) >= 0 ? 'text-success' : 'text-destructive'}>
                      ${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.net, 0))}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-accent-foreground opacity-75">
                    <div className="truncate max-w-32" title={sessionGroup.session_external_id || 'N/A'}>
                      {sessionGroup.session_external_id || 'N/A'}
                    </div>
                  </td>
                  {hasAdminSession && (
                    <td className="px-6 py-4 text-sm font-medium text-center">
                      <div className="flex justify-end">
                        <div className="relative" data-dropdown>
                          <button
                            onClick={() => setActiveDropdown(activeDropdown === `session-${sessionGroup.session_id}` ? null : `session-${sessionGroup.session_id}`)}
                            className="p-1 text-gray-400 hover:text-gray-600"
                          >
                          <MoreVertical className="h-4 w-4" />
                        </button>
                        {activeDropdown === `session-${sessionGroup.session_id}` && (
                          <div className="absolute right-0 top-8 bg-popover border border-border rounded-md shadow-lg z-10 min-w-[120px]">
                            <button
                              onClick={() => {
                                setNewRowData({
                                  ...newRowData,
                                  sessionId: sessionGroup.session_external_id
                                });
                                setShowAddRowModal(true);
                                setActiveDropdown(null);
                              }}
                              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-popover-foreground hover:bg-accent"
                            >
                              <Plus className="h-3 w-3" />
                              Add Row
                            </button>
                            <button
                              onClick={() => {
                                handleSessionDelete(sessionGroup.session_id, sessionGroup.game_number, sessionGroup.players.length);
                                setActiveDropdown(null);
                              }}
                              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-destructive hover:bg-accent"
                            >
                              <Trash2 className="h-3 w-3" />
                              Delete Session
                            </button>
                          </div>
                        )}
                        </div>
                      </div>
                    </td>
                  )}
                </tr>
                
                {/* Player Rows (expandable) */}
                {expandedSessions.has(sessionGroup.session_id) && sessionGroup.players.map((summary) => (
                  <tr key={`${summary.session_id}-${summary.player_id}`} className="hover:bg-muted/50 bg-card border-b border-border">
                    <td className="px-4 py-3" />
                    <td className="px-6 py-3 text-sm text-foreground pl-12">
                      {summary.player_name}
                    </td>
                    <td className="px-6 py-3 text-sm text-foreground text-right">
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="number"
                          value={editingRow.buy_in_sum}
                          onChange={(e) => setEditingRow({ ...editingRow, buy_in_sum: parseInt(e.target.value) || 0 })}
                          className="w-20 px-2 py-1 border border-input rounded text-sm bg-background"
                        />
                      ) : (
                        `$${formatCurrency(summary.buy_in_sum)}`
                      )}
                    </td>
                    <td className="px-6 py-3 text-sm text-foreground text-right">
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
                          className="w-20 px-2 py-1 border border-input rounded text-sm bg-background"
                          title="Total cash out + in game"
                        />
                      ) : (
                        `$${formatCurrency(summary.cash_out_sum + summary.in_game)}`
                      )}
                    </td>
                    <td className={`px-6 py-3 text-sm font-medium text-right ${summary.net >= 0 ? 'text-success' : 'text-destructive'}`}>
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="number"
                          value={editingRow.net}
                          onChange={(e) => setEditingRow({ ...editingRow, net: parseInt(e.target.value) || 0 })}
                          className="w-20 px-2 py-1 border border-input rounded text-sm bg-background"
                        />
                      ) : (
                        `$${formatCurrency(summary.net)}`
                      )}
                    </td>
                    <td className="px-6 py-3 text-sm text-foreground">
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="text"
                          value={editingRow.names.join(', ')}
                          onChange={(e) => setEditingRow({ ...editingRow, names: e.target.value.split(', ') })}
                          className="w-full px-2 py-1 border border-input rounded text-sm bg-background"
                        />
                      ) : (
                        <div className="truncate max-w-32" title={summary.names.join(', ')}>
                          {summary.names.join(', ')}
                        </div>
                      )}
                    </td>
                    {hasAdminSession && (
                      <td className="px-6 py-3 text-sm font-medium text-center">
                        <div className="flex justify-end">
                          {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                            <div className="flex gap-2">
                              <button
                                onClick={handleSave}
                                className="p-1 text-green-600 hover:text-green-900"
                              >
                                <Save className="h-4 w-4" />
                              </button>
                              <button
                                onClick={handleCancel}
                                className="p-1 text-gray-600 hover:text-gray-900"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          ) : (
                            <div className="relative" data-dropdown>
                            <button
                              onClick={() => setActiveDropdown(activeDropdown === `player-${summary.session_id}-${summary.player_id}` ? null : `player-${summary.session_id}-${summary.player_id}`)}
                              className="p-1 text-gray-400 hover:text-gray-600"
                            >
                              <MoreVertical className="h-4 w-4" />
                            </button>
                            {activeDropdown === `player-${summary.session_id}-${summary.player_id}` && (
                              <div className="absolute right-0 top-8 bg-white border border-gray-200 rounded-md shadow-lg z-10 min-w-[100px]">
                                <button
                                  onClick={() => {
                                    handleEdit(summary);
                                    setActiveDropdown(null);
                                  }}
                                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-popover-foreground hover:bg-accent"
                                >
                                  <Edit className="h-3 w-3" />
                                  Edit
                                </button>
                                <button
                                  onClick={() => {
                                    handleDelete(summary.session_id, summary.player_id, summary.player_name);
                                    setActiveDropdown(null);
                                  }}
                                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-destructive hover:bg-accent"
                                >
                                  <Trash2 className="h-3 w-3" />
                                  Delete
                                </button>
                              </div>
                            )}
                            </div>
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
        
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={goToPage}
          itemsPerPage={itemsPerPage}
          totalItems={sortedSessions.length}
        />
      </div>

      {!loading && summaries.length === 0 && (
        <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
          <p className="text-muted-foreground">No game ledger entries found.</p>
        </div>
      )}

      {/* Error Message Display */}
      {errorMessage && (
        <div className="fixed top-4 right-4 bg-red-50 border-l-4 border-red-400 rounded px-4 py-3 shadow-lg z-50">
          <div className="flex items-center">
            <svg className="w-4 h-4 mr-2 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-destructive">{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && deleteTarget && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-40">
          <div className="relative top-20 mx-auto p-5 border border-border w-96 shadow-lg rounded-md bg-card text-card-foreground">
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
                className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 bg-transparent rounded-2xl hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await performDelete(deleteTarget.sessionId, deleteTarget.playerId);
                  setShowDeleteModal(false);
                  setDeleteTarget(null);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-2xl hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
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
          <div className="relative top-20 mx-auto p-5 border border-border w-96 shadow-lg rounded-md bg-card text-card-foreground">
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
                className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 bg-transparent rounded-2xl hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await performSessionDelete(sessionDeleteTarget.sessionId);
                  setShowSessionDeleteModal(false);
                  setSessionDeleteTarget(null);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-2xl hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Delete Session
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Row Modal */}
      {showAddRowModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-40">
          <div className="relative top-20 mx-auto p-5 border border-border w-96 shadow-lg rounded-md bg-card text-card-foreground">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-xl font-semibold text-gray-900">Add New Row</h3>
              <button
                onClick={() => {
                  setShowAddRowModal(false);
                  setNewRowData({
                    sessionId: '',
                    playerName: '',
                    buyInSum: '',
                    cashOutSum: '',
                    inGame: ''
                  });
                  setErrorMessage(null);
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            <div className="mt-4">
              {errorMessage && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
                  <p className="text-sm text-red-800">{errorMessage}</p>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Session ID <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={newRowData.sessionId}
                    readOnly
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-600"
                    placeholder="Session will be auto-filled"
                  />
                  <p className="text-xs text-gray-500 mt-1">Session ID is automatically filled based on the selected session</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Player Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={newRowData.playerName}
                    onChange={(e) => setNewRowData({...newRowData, playerName: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter player name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Buy In ($) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={newRowData.buyInSum}
                    onChange={(e) => setNewRowData({...newRowData, buyInSum: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="0.00"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cash Out ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={newRowData.cashOutSum}
                    onChange={(e) => setNewRowData({...newRowData, cashOutSum: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="0.00"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    In Game ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={newRowData.inGame}
                    onChange={(e) => setNewRowData({...newRowData, inGame: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="0.00"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t mt-6">
              <button
                onClick={() => {
                  setShowAddRowModal(false);
                  setNewRowData({
                    sessionId: '',
                    playerName: '',
                    buyInSum: '',
                    cashOutSum: '',
                    inGame: ''
                  });
                  setErrorMessage(null);
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 bg-transparent rounded-2xl hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                onClick={handleAddRow}
                className="px-4 py-2 text-sm font-medium text-white bg-black border border-transparent rounded-2xl hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                Add Row
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}