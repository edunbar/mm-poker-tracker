import axios from 'axios';
import { Edit, MoreVertical, Plus, Save, Trash2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { API_BASE_URL } from '../../../config/api';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';
import { Button } from '../../../shared/ui/button';
import { Pagination, usePagination } from '../../../shared/ui/pagination';
import { Heading, Text } from '../../../shared/ui/typography';

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

interface EditingDate {
  session_id: string;
  date: string;
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
  const [editingDate, setEditingDate] = useState<EditingDate | null>(null);
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
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/ledger`);
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
      await axios.put(`${API_BASE_URL}/api/games/${publicCode}/ledger/manual/new`, {
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
        `${API_BASE_URL}/api/games/${publicCode}/ledger/${editingRow.session_id}/${editingRow.player_id}`,
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
        `${API_BASE_URL}/api/games/${publicCode}/ledger/${sessionId}/${playerId}`,
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
        `${API_BASE_URL}/api/games/${publicCode}/sessions/${sessionId}`,
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
    setEditingDate(null);
  };

  const handleDateEdit = (sessionId: string, currentDate: string | null) => {
    const dateStr = currentDate ? new Date(currentDate).toISOString() : new Date().toISOString();
    const dateValue = dateStr.split('T')[0] || '';
    setEditingDate({ session_id: sessionId, date: dateValue });
  };

  const handleDateSave = async () => {
    if (!editingDate || !effectiveAdminCode) return;

    try {
      await axios.put(
        `${API_BASE_URL}/api/games/${publicCode}/sessions/${editingDate.session_id}/date`,
        { started_at: editingDate.date },
        {
          headers: {
            'X-Admin-Code': effectiveAdminCode,
            'Content-Type': 'application/json',
          },
        }
      );

      setEditingDate(null);
      fetchLedgerData();
    } catch (error) {
      setErrorMessage('Failed to update session date. Please check your admin code.');
      setTimeout(() => setErrorMessage(null), 5000);
    }
  };

  const formatCurrency = (amount: number) => {
    return (amount / 100).toFixed(2);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', { timeZone: 'UTC' });
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
            <Heading variant="h1">Game Ledger</Heading>
            <Text variant="body" color="muted" className="mt-2">
              Session and player data
            </Text>
          </div>
          <Button
            onClick={fetchLedgerData}
          >
            <Text variant="bodySmall" weight="medium">Refresh</Text>
          </Button>
        </div>

      {showAdminInput && (
        <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-4 mb-6">
          <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
            Admin Code:
          </Text>
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
                <Button
                  onClick={handleSave}
                  className="bg-black text-white hover:opacity-90"
                >
                  <Text variant="bodySmall" weight="medium">Save</Text>
                </Button>
                <Button
                  onClick={handleCancel}
                  variant="outline"
                >
                  <Text variant="bodySmall" weight="medium">Cancel</Text>
                </Button>
              </>
            ) : pendingDelete ? (
              <>
                <Button
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
                  variant="destructive"
                >
                  <Text variant="bodySmall" weight="medium">Delete</Text>
                </Button>
                <Button
                  onClick={handleCancel}
                  variant="outline"
                >
                  <Text variant="bodySmall" weight="medium">Cancel</Text>
                </Button>
              </>
            ) : (
              <Button
                onClick={handleCancel}
                variant="outline"
              >
                Cancel
              </Button>
            )}
          </div>
        </div>
      )}

      <div className="overflow-auto rounded-xl border border-border bg-card">
          <table className="min-w-full">
          <thead className="bg-card border-b border-border">
            <tr>
              <th className="px-4 py-4" />
              <th className="px-6 py-4 text-left">
                <Text variant="bodySmall" weight="semibold" color="muted" className="uppercase tracking-wider">Session/Player</Text>
              </th>
              <th className="px-6 py-4 text-right">
                <Text variant="bodySmall" weight="semibold" color="muted" className="uppercase tracking-wider">Buy In</Text>
              </th>
              <th className="px-6 py-4 text-right">
                <Text variant="bodySmall" weight="semibold" color="muted" className="uppercase tracking-wider">Cash Out</Text>
              </th>
              <th className="px-6 py-4 text-right">
                <Text variant="bodySmall" weight="semibold" color="muted" className="uppercase tracking-wider">Net</Text>
              </th>
              <th className="px-6 py-4 text-left">
                <Text variant="bodySmall" weight="semibold" color="muted" className="uppercase tracking-wider">Names</Text>
              </th>
              {hasAdminSession && (
                <th className="px-6 py-4 text-center">
                  <Text variant="bodySmall" weight="semibold" color="muted" className="uppercase tracking-wider">Actions</Text>
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
                    <Button
                      onClick={() => toggleSession(sessionGroup.session_id)}
                      size="icon-sm"
                      className="w-6 h-6 rounded-full"
                    >
                      {expandedSessions.has(sessionGroup.session_id) ? '−' : '+'}
                    </Button>
                  </td>
                  <td className="px-6 py-4">
                    <Text variant="bodySmall" weight="semibold" className="text-accent-foreground">Game #{sessionGroup.game_number}</Text>
                    {editingDate?.session_id === sessionGroup.session_id ? (
                      <div className="flex items-center gap-2 mt-1">
                        <input
                          type="date"
                          value={editingDate.date}
                          onChange={(e) => setEditingDate({ ...editingDate, date: e.target.value })}
                          className="px-2 py-1 border border-input rounded text-xs bg-background text-foreground"
                        />
                        <Button
                          onClick={handleDateSave}
                          variant="ghost"
                          size="icon-sm"
                          className="p-1 text-green-600 hover:text-green-900"
                        >
                          <Save className="h-3 w-3" />
                        </Button>
                        <Button
                          onClick={() => setEditingDate(null)}
                          variant="ghost"
                          size="icon-sm"
                          className="p-1 text-gray-600 hover:text-gray-900"
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 group">
                        <Text variant="caption" className="text-accent-foreground opacity-80">
                          {formatDate(sessionGroup.session_started_at)} • ({sessionGroup.players.length} players)
                        </Text>
                        {hasAdminSession && (
                          <Button
                            onClick={() => handleDateEdit(sessionGroup.session_id, sessionGroup.session_started_at)}
                            variant="ghost"
                            size="icon-sm"
                            className="p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <Edit className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Text variant="bodySmall" weight="medium" className="text-accent-foreground">${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.buy_in_sum, 0))}</Text>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Text variant="bodySmall" weight="medium" className="text-accent-foreground">${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.cash_out_sum + p.in_game, 0))}</Text>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Text
                      variant="bodySmall"
                      weight="semibold"
                      color={sessionGroup.players.reduce((sum, p) => sum + p.net, 0) >= 0 ? 'success' : 'destructive'}
                    >
                      ${formatCurrency(sessionGroup.players.reduce((sum, p) => sum + p.net, 0))}
                    </Text>
                  </td>
                  <td className="px-6 py-4">
                    <div className="truncate max-w-32" title={sessionGroup.session_external_id || 'N/A'}>
                      <Text variant="bodySmall" className="text-accent-foreground opacity-75">{sessionGroup.session_external_id || 'N/A'}</Text>
                    </div>
                  </td>
                  {hasAdminSession && (
                    <td className="px-6 py-4 text-sm font-medium text-center">
                      <div className="flex justify-end">
                        <div className="relative" data-dropdown>
                          <Button
                            onClick={() => setActiveDropdown(activeDropdown === `session-${sessionGroup.session_id}` ? null : `session-${sessionGroup.session_id}`)}
                            variant="ghost"
                            size="icon-sm"
                            className="p-1 text-gray-400 hover:text-gray-600"
                          >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                        {activeDropdown === `session-${sessionGroup.session_id}` && (
                          <div className="absolute right-0 top-8 bg-popover border border-border rounded-md shadow-lg z-10 min-w-[120px]">
                            <Button
                              onClick={() => {
                                setNewRowData({
                                  ...newRowData,
                                  sessionId: sessionGroup.session_external_id
                                });
                                setShowAddRowModal(true);
                                setActiveDropdown(null);
                              }}
                              variant="ghost"
                              className="flex items-center gap-2 w-full justify-start px-3 py-2 hover:bg-accent"
                            >
                              <Plus className="h-3 w-3" />
                              <Text variant="bodySmall">Add Row</Text>
                            </Button>
                            <Button
                              onClick={() => {
                                handleSessionDelete(sessionGroup.session_id, sessionGroup.game_number, sessionGroup.players.length);
                                setActiveDropdown(null);
                              }}
                              variant="ghost"
                              className="flex items-center gap-2 w-full justify-start px-3 py-2 hover:bg-accent"
                            >
                              <Trash2 className="h-3 w-3" />
                              <Text variant="bodySmall" color="destructive">Delete Session</Text>
                            </Button>
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
                    <td className="px-6 py-3 pl-12">
                      <Text variant="bodySmall">{summary.player_name}</Text>
                    </td>
                    <td className="px-6 py-3 text-right">
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="number"
                          value={editingRow.buy_in_sum}
                          onChange={(e) => setEditingRow({ ...editingRow, buy_in_sum: parseInt(e.target.value) || 0 })}
                          className="w-20 px-2 py-1 border border-input rounded text-sm bg-background"
                        />
                      ) : (
                        <Text variant="bodySmall">${formatCurrency(summary.buy_in_sum)}</Text>
                      )}
                    </td>
                    <td className="px-6 py-3 text-right">
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
                        <Text variant="bodySmall">${formatCurrency(summary.cash_out_sum + summary.in_game)}</Text>
                      )}
                    </td>
                    <td className="px-6 py-3 text-right">
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="number"
                          value={editingRow.net}
                          onChange={(e) => setEditingRow({ ...editingRow, net: parseInt(e.target.value) || 0 })}
                          className="w-20 px-2 py-1 border border-input rounded text-sm bg-background"
                        />
                      ) : (
                        <Text variant="bodySmall" weight="medium" color={summary.net >= 0 ? 'success' : 'destructive'}>
                          ${formatCurrency(summary.net)}
                        </Text>
                      )}
                    </td>
                    <td className="px-6 py-3">
                      {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                        <input
                          type="text"
                          value={editingRow.names.join(', ')}
                          onChange={(e) => setEditingRow({ ...editingRow, names: e.target.value.split(', ') })}
                          className="w-full px-2 py-1 border border-input rounded text-sm bg-background"
                        />
                      ) : (
                        <div className="truncate max-w-32" title={summary.names.join(', ')}>
                          <Text variant="bodySmall">{summary.names.join(', ')}</Text>
                        </div>
                      )}
                    </td>
                    {hasAdminSession && (
                      <td className="px-6 py-3 text-center">
                        <div className="flex justify-end">
                          {editingRow?.session_id === summary.session_id && editingRow?.player_id === summary.player_id ? (
                            <div className="flex gap-2">
                              <Button
                                onClick={handleSave}
                                variant="ghost"
                                size="icon-sm"
                                className="p-1 text-green-600 hover:text-green-900"
                              >
                                <Save className="h-4 w-4" />
                              </Button>
                              <Button
                                onClick={handleCancel}
                                variant="ghost"
                                size="icon-sm"
                                className="p-1 text-gray-600 hover:text-gray-900"
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                          ) : (
                            <div className="relative" data-dropdown>
                            <Button
                              onClick={() => setActiveDropdown(activeDropdown === `player-${summary.session_id}-${summary.player_id}` ? null : `player-${summary.session_id}-${summary.player_id}`)}
                              variant="ghost"
                              size="icon-sm"
                              className="p-1 text-gray-400 hover:text-gray-600"
                            >
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                            {activeDropdown === `player-${summary.session_id}-${summary.player_id}` && (
                              <div className="absolute right-0 top-8 bg-white border border-gray-200 rounded-md shadow-lg z-10 min-w-[100px]">
                                <Button
                                  onClick={() => {
                                    handleEdit(summary);
                                    setActiveDropdown(null);
                                  }}
                                  variant="ghost"
                                  className="flex items-center gap-2 w-full justify-start px-3 py-2 hover:bg-accent"
                                >
                                  <Edit className="h-3 w-3" />
                                  <Text variant="bodySmall">Edit</Text>
                                </Button>
                                <Button
                                  onClick={() => {
                                    handleDelete(summary.session_id, summary.player_id, summary.player_name);
                                    setActiveDropdown(null);
                                  }}
                                  variant="ghost"
                                  className="flex items-center gap-2 w-full justify-start px-3 py-2 hover:bg-accent"
                                >
                                  <Trash2 className="h-3 w-3" />
                                  <Text variant="bodySmall" color="destructive">Delete</Text>
                                </Button>
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
          <Text variant="body" color="muted">No game ledger entries found.</Text>
        </div>
      )}

      {/* Error Message Display */}
      {errorMessage && (
        <div className="fixed top-4 right-4 bg-red-50 border-l-4 border-red-400 rounded px-4 py-3 shadow-lg z-50">
          <div className="flex items-center">
            <svg className="w-4 h-4 mr-2 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <Text variant="bodySmall" color="destructive" as="span">{errorMessage}</Text>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && deleteTarget && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-40">
          <div className="relative top-20 mx-auto p-5 border border-border w-96 shadow-lg rounded-md bg-card text-card-foreground">
            <div className="flex items-center justify-between border-b pb-3">
              <Heading variant="h4" className="text-gray-900">Confirm Deletion</Heading>
              <Button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteTarget(null);
                }}
                variant="ghost"
                size="icon-sm"
                className="text-gray-400 hover:text-gray-600"
              >
                <span className="sr-only">Close</span>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Button>
            </div>
            
            <div className="pt-4 pb-6">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <Text variant="bodyLarge" weight="medium" as="h4" className="text-gray-900 mb-2">Delete Player Record</Text>
                  <Text variant="bodySmall" className="text-gray-600 mb-4">
                    Are you sure you want to delete the record for <strong>{deleteTarget.playerName}</strong>?
                    This action cannot be undone and will permanently remove this player's data from the session.
                  </Text>
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <Text variant="bodySmall" className="text-red-800">
                      <strong>Warning:</strong> This will delete the player record from both the database and Google Sheets.
                    </Text>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteTarget(null);
                }}
                variant="outline"
                className="text-gray-700 border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  await performDelete(deleteTarget.sessionId, deleteTarget.playerId);
                  setShowDeleteModal(false);
                  setDeleteTarget(null);
                }}
                variant="destructive"
                className="bg-red-600 hover:bg-red-700"
              >
                <Text variant="bodySmall" weight="medium">Delete Record</Text>
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Session Delete Confirmation Modal */}
      {showSessionDeleteModal && sessionDeleteTarget && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-40">
          <div className="relative top-20 mx-auto p-5 border border-border w-96 shadow-lg rounded-md bg-card text-card-foreground">
            <div className="flex items-center justify-between border-b pb-3">
              <Heading variant="h4" className="text-gray-900">Confirm Session Deletion</Heading>
              <Button
                onClick={() => {
                  setShowSessionDeleteModal(false);
                  setSessionDeleteTarget(null);
                }}
                variant="ghost"
                size="icon-sm"
                className="text-gray-400 hover:text-gray-600"
              >
                <span className="sr-only">Close</span>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Button>
            </div>
            
            <div className="pt-4 pb-6">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <Text variant="bodyLarge" weight="medium" as="h4" className="text-gray-900 mb-2">Delete Entire Session</Text>
                  <Text variant="bodySmall" className="text-gray-600 mb-4">
                    Are you sure you want to delete <strong>Game #{sessionDeleteTarget.gameNumber}</strong> and all associated player records?
                    This will permanently remove <strong>{sessionDeleteTarget.playerCount} player record(s)</strong> from the session.
                  </Text>
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <Text variant="bodySmall" className="text-red-800">
                      <strong>Warning:</strong> This action cannot be undone and will delete the entire session from both the database and Google Sheets.
                    </Text>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button
                onClick={() => {
                  setShowSessionDeleteModal(false);
                  setSessionDeleteTarget(null);
                }}
                variant="outline"
                className="text-gray-700 border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  await performSessionDelete(sessionDeleteTarget.sessionId);
                  setShowSessionDeleteModal(false);
                  setSessionDeleteTarget(null);
                }}
                variant="destructive"
                className="bg-red-600 hover:bg-red-700"
              >
                <Text variant="bodySmall" weight="medium">Delete Session</Text>
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add Row Modal */}
      {showAddRowModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-40">
          <div className="relative top-20 mx-auto p-5 border border-border w-96 shadow-lg rounded-md bg-card text-card-foreground">
            <div className="flex items-center justify-between border-b pb-3">
              <Heading variant="h4" className="text-gray-900">Add New Row</Heading>
              <Button
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
                variant="ghost"
                size="icon-sm"
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </Button>
            </div>

            <div className="mt-4">
              {errorMessage && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
                  <Text variant="bodySmall" className="text-red-800">{errorMessage}</Text>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block text-gray-700 mb-1">
                    Session ID <span className="text-red-500">*</span>
                  </Text>
                  <input
                    type="text"
                    value={newRowData.sessionId}
                    readOnly
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-600"
                    placeholder="Session will be auto-filled"
                  />
                  <Text variant="caption" className="text-gray-500 mt-1">Session ID is automatically filled based on the selected session</Text>
                </div>

                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block text-gray-700 mb-1">
                    Player Name <span className="text-red-500">*</span>
                  </Text>
                  <input
                    type="text"
                    value={newRowData.playerName}
                    onChange={(e) => setNewRowData({...newRowData, playerName: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter player name"
                  />
                </div>

                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block text-gray-700 mb-1">
                    Buy In ($) <span className="text-red-500">*</span>
                  </Text>
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
                  <Text variant="bodySmall" weight="medium" as="label" className="block text-gray-700 mb-1">
                    Cash Out ($)
                  </Text>
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
                  <Text variant="bodySmall" weight="medium" as="label" className="block text-gray-700 mb-1">
                    In Game ($)
                  </Text>
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
              <Button
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
                variant="outline"
                className="text-gray-700 border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddRow}
                className="bg-black text-white hover:opacity-90"
              >
                <Text variant="bodySmall" weight="medium">Add Row</Text>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}