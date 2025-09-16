import axios from 'axios';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useToast } from '../../../contexts/ToastContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';

interface SessionAnalysis {
  session_id: string;
  external_id: string;
  game_number: number;
  started_at: string | null;
  buy_ins: number;
  cash_outs: number;
  in_game: number;
  balance: number;
  is_balanced: boolean;
  player_count: number;
}

interface MathError {
  session_id: string;
  player_id: string;
  game_number: number;
  external_id: string;
  player_name: string;
  buy_in: number;
  cash_out: number;
  in_game: number;
  recorded_net: number;
  calculated_net: number;
  difference: number;
  names: string[];
}

interface SessionDetail {
  session_id: string;
  external_id: string;
  game_number: number;
  started_at: string | null;
  players: Array<{
    player_id: string;
    display_name: string;
    buy_in_sum: number;
    cash_out_sum: number;
    in_game: number;
    net: number;
  }>;
  totals: {
    buy_ins: number;
    cash_outs: number;
    in_game: number;
    balance: number;
  };
  audit_logs: Array<{
    id: string;
    actor_kind: string;
    actor_id: string;
    action: string;
    target_table: string;
    timestamp: string | null;
    description: string;
    before: any;
    after: any;
  }>;
  data_comparison?: {
    has_differences: boolean;
    missing_players: Array<{
      name: string;
      original_data: any;
    }>;
    added_players: Array<{
      name: string;
      player_id: string;
      current_data: any;
    }>;
    modified_players: Array<{
      name: string;
      player_id: string;
      differences: any;
    }>;
    summary: {
      original_player_count: number;
      current_player_count: number;
      missing_count: number;
      added_count: number;
      modified_count: number;
    };
    error?: string;
  };
}

export default function LedgerAnalysisPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const { hasAdminSession, adminCode } = useAdminSession();
  const { showSuccess, showError } = useToast();
  const { title: _title } = useGameTitle(publicCode || '');
  const [loading, setLoading] = useState(false);
  const [sessionAnalysis, setSessionAnalysis] = useState<SessionAnalysis[]>([]);
  const [mathErrors, setMathErrors] = useState<MathError[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [expandedAuditId, setExpandedAuditId] = useState<string | null>(null);
  const [playerDebugData, setPlayerDebugData] = useState<any>(null);
  const [editingPlayer, setEditingPlayer] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<{[key: string]: {buy_in: string, cash_out: string, in_game: string}}>({});
  const [merging, setMerging] = useState<{source: string, target: string} | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{sessionId: string, playerId: string, playerName: string} | null>(null);
  const [showAddPlayerModal, setShowAddPlayerModal] = useState(false);
  const [newPlayerData, setNewPlayerData] = useState({
    playerName: '',
    buyInSum: '',
    cashOutSum: '',
    inGame: ''
  });

  useEffect(() => {
    if (publicCode && hasAdminSession) {
      fetchAnalysisData();
      fetchPlayerDebugData();
    }
  }, [publicCode, hasAdminSession]);

  const fetchAnalysisData = async () => {
    if (!hasAdminSession || !publicCode) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/ledger-analysis`, {
        headers: { 'X-Admin-Code': adminCode || '' }
      });
      
      const data = response.data;
      if (data.session_analysis) {
        // Filter to only show unbalanced sessions
        const unbalanced = data.session_analysis.filter((session: SessionAnalysis) => !session.is_balanced);
        setSessionAnalysis(unbalanced);
      }
      
      // Extract math errors from business logic violations
      if (data.business_logic_violations && data.business_logic_violations.mathematical_inconsistencies) {
        setMathErrors(data.business_logic_violations.mathematical_inconsistencies);
      }
    } catch (error) {
    } finally {
      setLoading(false);
    }
  };

  const openSessionModal = async (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setSessionLoading(true);
    setSessionDetail(null);
    
    try {
      const response = await axios.get(
        `http://localhost:8000/api/games/${publicCode}/sessions/${sessionId}/detail`,
        { headers: { 'X-Admin-Code': adminCode || '' } }
      );
      setSessionDetail(response.data);
    } catch (error) {
    } finally {
      setSessionLoading(false);
    }
  };

  const closeSessionModal = () => {
    setSelectedSessionId(null);
    setSessionDetail(null);
    setExpandedAuditId(null);
    setEditingPlayer(null);
    setEditValues({});
  };

  const startEditingPlayer = (playerId: string, player: any) => {
    setEditingPlayer(playerId);
    setEditValues({
      ...editValues,
      [playerId]: {
        buy_in: formatCurrency(player.buy_in_sum),
        cash_out: formatCurrency(player.cash_out_sum),
        in_game: formatCurrency(player.in_game)
      }
    });
  };

  const savePlayerChanges = async (playerId: string) => {
    if (!sessionDetail || !editValues[playerId]) return;

    const values = editValues[playerId];
    if (!values) return;

    try {
      await axios.put(
        `http://localhost:8000/api/games/${publicCode}/sessions/${selectedSessionId}/players/${playerId}`,
        {
          buy_in_sum: Math.round(parseFloat(values.buy_in) * 100),
          cash_out_sum: Math.round(parseFloat(values.cash_out) * 100),
          in_game: Math.round(parseFloat(values.in_game) * 100)
        },
        { headers: { 'X-Admin-Code': adminCode || '' } }
      );

      // Refresh the session detail
      const detailResponse = await axios.get(
        `http://localhost:8000/api/games/${publicCode}/sessions/${selectedSessionId}/detail`,
        { headers: { 'X-Admin-Code': adminCode || '' } }
      );
      setSessionDetail(detailResponse.data);
      
      // Refresh the main analysis data
      fetchAnalysisData();
      
      setEditingPlayer(null);
      const newEditValues = { ...editValues };
      delete newEditValues[playerId];
      setEditValues(newEditValues);
      
    } catch (error) {
      showError('Update Failed', 'Failed to update player values');
    }
  };

  const cancelEditing = (playerId: string) => {
    setEditingPlayer(null);
    const newEditValues = { ...editValues };
    delete newEditValues[playerId];
    setEditValues(newEditValues);
  };

  const fetchPlayerDebugData = async () => {
    if (!hasAdminSession || !publicCode) return;
    
    try {
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/players/verification-debug`);
      setPlayerDebugData(response.data);
    } catch (error) {
      setPlayerDebugData({ error: 'Failed to load debug data' });
    }
  };

  // Check if there are any player debug issues to display
  const hasPlayerDebugIssues = () => {
    if (!playerDebugData || playerDebugData.error) return false;
    
    const hasDuplicates = playerDebugData.duplicate_display_names && playerDebugData.duplicate_display_names.length > 0;
    const hasConflicts = playerDebugData.external_id_conflicts && playerDebugData.external_id_conflicts.length > 0;
    
    return hasDuplicates || hasConflicts;
  };

  const formatCurrency = (amount: number) => {
    return (amount / 100).toFixed(2);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const mergePlayer = async (sourcePlayerId: string, targetPlayerId: string) => {
    try {
      setMerging({source: sourcePlayerId, target: targetPlayerId});
      
      const response = await fetch(`http://localhost:8000/api/games/${publicCode}/players/${sourcePlayerId}/merge-into/${targetPlayerId}`, {
        method: 'POST',
        headers: {
          'X-Admin-Code': adminCode || '',
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to merge players');
      }

      const result = await response.json();
      
      // Show success message with toast notification
      showSuccess(
        'Players Merged Successfully!',
        `${result.message}\n\nTransferred: ${result.transfer_summary.total_summaries} sessions, ${result.transfer_summary.transferred_payment_transactions} payments`,
        10000
      );
      
      // Refresh the debug data
      fetchPlayerDebugData();
      
    } catch (error) {
      showError('Merge Failed', `Error merging players: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setMerging(null);
    }
  };

  const deletePlayer = async (sessionId: string, playerId: string) => {
    try {
      await axios.delete(`http://localhost:8000/api/games/${publicCode}/ledger/${sessionId}/${playerId}`, {
        headers: {
          'X-Admin-Code': adminCode || '',
        },
      });

      // Refresh the session detail and analysis data
      if (selectedSessionId) {
        await openSessionModal(selectedSessionId);
      }
      fetchAnalysisData();
      
      setShowDeleteModal(false);
      setDeleteTarget(null);
    } catch (error) {
      showError('Delete Failed', 'Failed to delete player. Please try again.');
    }
  };

  const addPlayerToSession = async () => {
    if (!selectedSessionId) return;
    
    try {
      const buyIn = parseFloat(newPlayerData.buyInSum) * 100; // Convert to cents
      const cashOut = parseFloat(newPlayerData.cashOutSum || '0') * 100;
      const inGame = parseFloat(newPlayerData.inGame || '0') * 100;
      
      await axios.put(`http://localhost:8000/api/games/${publicCode}/ledger/manual/new`, {
        session_external_id: sessionDetail?.external_id || selectedSessionId,
        player_name: newPlayerData.playerName,
        buy_in_sum: buyIn,
        cash_out_sum: cashOut,
        in_game: inGame
      }, {
        headers: {
          'X-Admin-Code': adminCode || '',
          'Content-Type': 'application/json'
        }
      });

      // Reset form and close modal
      setNewPlayerData({
        playerName: '',
        buyInSum: '',
        cashOutSum: '',
        inGame: ''
      });
      setShowAddPlayerModal(false);
      
      // Refresh the session detail and analysis data
      await openSessionModal(selectedSessionId);
      fetchAnalysisData();
    } catch (error) {
      showError('Add Failed', 'Failed to add player. Please try again.');
    }
  };

  if (!hasAdminSession) {
    return (
      <div className="min-h-screen bg-background py-8">
        <div className="max-w-6xl mx-auto px-4">
                    <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            <p className="text-lg text-muted-foreground">Please log in with admin credentials to view ledger analysis.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4">
                
        <div className="mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Game Ledger Analysis</h1>
            <p className="mt-2 text-muted-foreground">
              Analyze session balances and identify data issues
            </p>
          </div>
        </div>
          
        {loading ? (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
            <p className="mt-4 text-muted-foreground">Analyzing game data...</p>
          </div>
        ) : sessionAnalysis.length === 0 && mathErrors.length === 0 && !hasPlayerDebugIssues() ? (
          <div className="space-y-8">
            <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
              <div className="text-success text-6xl mb-4">✓</div>
              <h3 className="text-xl font-semibold text-foreground mb-2">All Sessions Balanced</h3>
              <p className="text-muted-foreground">No ledger issues detected in this game.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Wall of Fame Section */}
            <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
              <div className="border-b p-4">
                <h3 className="text-lg font-semibold text-foreground">Wall of Fame</h3>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-6">
                  <div className="bg-accent p-6 rounded-lg border border-border text-center">
                    <h4 className="text-sm font-medium text-muted-foreground mb-2">Biggest Winner</h4>
                    <div className="text-2xl font-bold text-success">Player Name</div>
                    <div className="text-lg text-success">$1,234.56</div>
                  </div>
                  <div className="bg-accent p-6 rounded-lg border border-border text-center">
                    <h4 className="text-sm font-medium text-muted-foreground mb-2">Most Consistent</h4>
                    <div className="text-2xl font-bold text-primary">Player Name</div>
                    <div className="text-lg text-muted-foreground">98% sessions positive</div>
                  </div>
                  <div className="bg-accent p-6 rounded-lg border border-border text-center">
                    <h4 className="text-sm font-medium text-muted-foreground mb-2">High Roller</h4>
                    <div className="text-2xl font-bold text-warning">Player Name</div>
                    <div className="text-lg text-muted-foreground">$5,000 avg buy-in</div>
                  </div>
                  <div className="bg-accent p-6 rounded-lg border border-border text-center">
                    <h4 className="text-sm font-medium text-muted-foreground mb-2">Longest Hot Streak</h4>
                    <div className="text-2xl font-bold text-info">Player Name</div>
                    <div className="text-lg text-muted-foreground">12 sessions</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Player Debug Section - Show when there are issues */}
            {hasPlayerDebugIssues() && (
              <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
                <div className="border-b p-4">
                  <h3 className="text-lg font-semibold text-foreground">Player Verification Debug</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Identify player verification issues and duplicate players
                  </p>
                </div>
                <div className="p-6">
                  {playerDebugData ? (
                    <div className="space-y-6">
                      {playerDebugData.error ? (
                        <div className="bg-card border-b border-border border border-red-200 rounded-md p-4">
                          <p className="text-destructive">{playerDebugData.error}</p>
                        </div>
                      ) : (
                        <>
                          {/* Player Name Duplicates */}
                          {playerDebugData.duplicate_display_names && playerDebugData.duplicate_display_names.length > 0 && (
                            <div className="bg-warning/10 border border-warning/20 rounded-lg p-4">
                              <h4 className="text-lg font-medium text-warning mb-3">
                                ⚠️ Duplicate Display Names
                              </h4>
                              <p className="text-sm text-warning mb-3">
                                Players with the same display name but different player IDs. This can cause confusion during imports.
                              </p>
                              {playerDebugData.duplicate_display_names.map((group: any, index: number) => (
                                <div key={index} className="mb-4 last:mb-0">
                                  <div className="font-medium text-warning mb-2">
                                    Name: "{group.display_name}" ({group.players.length} players)
                                  </div>
                                  <div className="space-y-2">
                                    {group.players.map((player: any) => (
                                      <div key={player.player_id} className="bg-warning/20 rounded p-3 text-sm text-warning-foreground">
                                        <div className="flex items-center justify-between">
                                          <div>
                                            <span className="font-mono text-xs bg-muted px-2 py-1 rounded">
                                              ID: {player.player_id.slice(0, 8)}...
                                            </span>
                                            {player.external_id && (
                                              <span className="ml-2 font-mono text-xs bg-primary/20 text-primary px-2 py-1 rounded">
                                                External: {player.external_id}
                                              </span>
                                            )}
                                          </div>
                                          <div className="text-right">
                                            <div className="text-xs text-muted-foreground">
                                              {player.session_count} session{player.session_count !== 1 ? 's' : ''}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                              Created: {new Date(player.created_at).toLocaleDateString()}
                                            </div>
                                          </div>
                                        </div>
                                        {player.all_names && player.all_names.length > 0 && (
                                          <div className="mt-2 text-xs">
                                            <span className="text-muted-foreground">Session names: </span>
                                            <span className="text-foreground">{player.all_names.join(', ')}</span>
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                  
                                  {/* Merge Controls for Duplicates */}
                                  {group.players.length === 2 && (
                                    <div className="mt-3 p-3 bg-info/10 border border-info/20 rounded">
                                      <div className="text-sm font-medium text-info mb-2">Merge Players</div>
                                      <div className="flex gap-2">
                                        <button
                                          onClick={() => mergePlayer(group.players[1].player_id, group.players[0].player_id)}
                                          disabled={merging !== null}
                                          className="px-3 py-1 text-xs bg-black text-white rounded-2xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                          {merging?.source === group.players[1].player_id ? 'Merging...' : `Merge "${group.players[1].display_name}" → "${group.players[0].display_name}"`}
                                        </button>
                                        <button
                                          onClick={() => mergePlayer(group.players[0].player_id, group.players[1].player_id)}
                                          disabled={merging !== null}
                                          className="px-3 py-1 text-xs bg-black text-white rounded-2xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                          {merging?.source === group.players[0].player_id ? 'Merging...' : `Merge "${group.players[0].display_name}" → "${group.players[1].display_name}"`}
                                        </button>
                                      </div>
                                      <div className="text-xs text-info mt-1">
                                        Choose which player to keep. All sessions and payments from the source will be merged into the target.
                                      </div>
                                    </div>
                                  )}
                                  
                                  {group.players.length > 2 && (
                                    <div className="mt-3 p-3 bg-orange-50 border border-orange-200 rounded">
                                      <div className="text-sm font-medium text-orange-800 mb-1">Multiple Duplicates</div>
                                      <div className="text-xs text-orange-700">
                                        {group.players.length} players with the same name. Consider merging them manually or contact support.
                                      </div>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}

                          {/* External ID Conflicts */}
                          {playerDebugData.external_id_conflicts && playerDebugData.external_id_conflicts.length > 0 && (
                            <div className="bg-card border-b border-border border border-red-200 rounded-lg p-4">
                              <h4 className="text-lg font-medium text-destructive mb-3">
                                🚨 External ID Conflicts
                              </h4>
                              <p className="text-sm text-destructive mb-3">
                                Multiple players sharing the same external ID. This should not happen.
                              </p>
                              {playerDebugData.external_id_conflicts.map((conflict: any, index: number) => (
                                <div key={index} className="mb-4 last:mb-0">
                                  <div className="font-medium text-destructive mb-2">
                                    External ID: "{conflict.external_id}" ({conflict.players.length} players)
                                  </div>
                                  <div className="space-y-2">
                                    {conflict.players.map((player: any) => (
                                      <div key={player.player_id} className="bg-red-100 rounded p-3 text-sm">
                                        <div className="flex items-center justify-between">
                                          <div>
                                            <span className="font-medium">{player.display_name}</span>
                                            <span className="ml-2 font-mono text-xs bg-muted px-2 py-1 rounded text-muted-foreground">
                                              ID: {player.player_id.slice(0, 8)}...
                                            </span>
                                          </div>
                                          <div className="text-xs text-muted-foreground">
                                            {player.session_count} session{player.session_count !== 1 ? 's' : ''}
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Summary Stats */}
                          <div className="bg-muted rounded-lg p-4">
                            <h4 className="text-lg font-medium text-foreground mb-3">Summary</h4>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                              <div className="text-center">
                                <div className="text-2xl font-bold text-primary">
                                  {playerDebugData.total_players || 0}
                                </div>
                                <div className="text-sm text-muted-foreground">Total Players</div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-success">
                                  {playerDebugData.verified_count || 0}
                                </div>
                                <div className="text-sm text-muted-foreground">Verified</div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-primary">
                                  {playerDebugData.unverified_count || 0}
                                </div>
                                <div className="text-sm text-muted-foreground">Unverified</div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-warning">
                                  {(playerDebugData.duplicate_display_names || []).length}
                                </div>
                                <div className="text-sm text-muted-foreground">Duplicate Names</div>
                              </div>
                            </div>
                          </div>

                          <div className="text-sm text-muted-foreground">
                            <button 
                              onClick={() => {
                                setPlayerDebugData(null);
                                fetchPlayerDebugData();
                              }}
                              className="text-primary hover:text-primary/80"
                            >
                              Refresh Debug Data
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
                      <p className="text-muted-foreground">Loading debug data...</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Unbalanced Sessions Section */}
            {sessionAnalysis.length > 0 && (
              <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
                <div className="border-b p-4">
                  <h3 className="text-lg font-semibold">Unbalanced Sessions</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Sessions where total buy-ins don't equal total cash-outs plus in-game chips
                  </p>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead className="bg-card border-b border-border rounded-t-lg">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider rounded-tl-lg">Game #</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">External ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Started</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Players</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Buy-ins</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Cash-outs</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">In Game</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Balance</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider rounded-tr-lg">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-card">
                      {sessionAnalysis.map((session) => (
                        <tr key={session.session_id} className="border-b border-border hover:bg-accent/50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                            #{session.game_number}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground font-mono">
                            {session.external_id}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                            {formatDate(session.started_at)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                            {session.player_count}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                            ${formatCurrency(session.buy_ins)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                            ${formatCurrency(session.cash_outs)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                            ${formatCurrency(session.in_game)}
                          </td>
                          <td className={`px-6 py-4 whitespace-nowrap text-sm font-bold text-right ${
                            session.balance > 0 ? 'text-destructive' : 'text-primary'
                          }`}>
                            ${formatCurrency(Math.abs(session.balance))} {session.balance > 0 ? 'over' : 'under'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => openSessionModal(session.session_id)}
                              className="text-primary hover:text-primary/80"
                            >
                              View Details
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Math Errors Section */}
            {mathErrors.length > 0 && (
              <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
                <div className="border-b p-4">
                  <h3 className="text-lg font-semibold">Individual Math Errors</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Player entries where recorded net doesn't match calculated net (cash-out + in-game - buy-in)
                  </p>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead className="bg-card border-b border-border rounded-t-lg">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider rounded-tl-lg">Game #</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Player</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Buy-in</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Cash-out</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">In Game</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Recorded Net</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Calculated Net</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Difference</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider rounded-tr-lg">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-card">
                      {mathErrors.map((error) => (
                        <tr key={`${error.session_id}-${error.player_id}`} className="border-b border-border hover:bg-accent/50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                            #{error.game_number}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-foreground">{error.player_name}</div>
                            <div className="text-sm text-muted-foreground">
                              {error.names.length > 1 && `(${error.names.join(', ')})`}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                            ${formatCurrency(error.buy_in)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                            ${formatCurrency(error.cash_out)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                            ${formatCurrency(error.in_game)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                            ${formatCurrency(error.recorded_net)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-success text-right font-medium">
                            ${formatCurrency(error.calculated_net)}
                          </td>
                          <td className={`px-6 py-4 whitespace-nowrap text-sm font-bold text-right ${
                            error.difference > 0 ? 'text-destructive' : 'text-primary'
                          }`}>
                            ${formatCurrency(Math.abs(error.difference))} {error.difference > 0 ? 'over' : 'under'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => openSessionModal(error.session_id)}
                              className="text-primary hover:text-primary/80"
                            >
                              View Session
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

          </div>
        )}

        {/* Session Detail Modal */}
        {selectedSessionId && (
          <div className="fixed inset-0 bg-black bg-opacity-50 overflow-y-auto h-full w-full z-40">
            <div className="relative top-20 mx-auto p-5 border border-border w-11/12 max-w-6xl shadow-lg rounded-md bg-card text-card-foreground">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="text-2xl font-semibold text-foreground">Session Details</h3>
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => setShowAddPlayerModal(true)}
                    className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-black hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2"
                  >
                    Add Player
                  </button>
                  <button
                    onClick={closeSessionModal}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              <div className="mt-4">
                {sessionLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
                  </div>
                ) : sessionDetail ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="bg-card border-b border-border p-4 rounded-lg">
                        <div className="text-sm text-muted-foreground">Game Number</div>
                        <div className="text-lg font-semibold">#{sessionDetail.game_number}</div>
                      </div>
                      <div className="bg-card border-b border-border p-4 rounded-lg">
                        <div className="text-sm text-muted-foreground">External ID</div>
                        <div className="text-lg font-mono">{sessionDetail.external_id}</div>
                      </div>
                      <div className="bg-card border-b border-border p-4 rounded-lg">
                        <div className="text-sm text-muted-foreground">Started At</div>
                        <div className="text-lg">{formatDate(sessionDetail.started_at)}</div>
                      </div>
                      <div className="bg-card border-b border-border p-4 rounded-lg">
                        <div className="text-sm text-muted-foreground">Players</div>
                        <div className="text-lg font-semibold">{sessionDetail.players.length}</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div className="bg-accent p-4 rounded-lg border border-border">
                        <div className="text-sm text-primary">Total Buy-ins</div>
                        <div className="text-xl font-bold text-primary">${formatCurrency(sessionDetail.totals.buy_ins)}</div>
                      </div>
                      <div className="bg-accent p-4 rounded-lg border border-border">
                        <div className="text-sm text-success">Total Cash-outs</div>
                        <div className="text-xl font-bold text-success">${formatCurrency(sessionDetail.totals.cash_outs)}</div>
                      </div>
                      <div className="bg-accent p-4 rounded-lg border border-border">
                        <div className="text-sm text-warning">Total In Game</div>
                        <div className="text-xl font-bold text-warning">${formatCurrency(sessionDetail.totals.in_game)}</div>
                      </div>
                      <div className="bg-accent p-4 rounded-lg border border-border">
                        <div className={`text-sm ${sessionDetail.totals.balance === 0 ? 'text-success' : 'text-destructive'}`}>Balance</div>
                        <div className={`text-xl font-bold ${sessionDetail.totals.balance === 0 ? 'text-success' : 'text-destructive'}`}>
                          ${formatCurrency(Math.abs(sessionDetail.totals.balance))} {sessionDetail.totals.balance > 0 ? 'over' : sessionDetail.totals.balance < 0 ? 'under' : 'balanced'}
                        </div>
                      </div>
                    </div>

                    {/* Player Details */}
                    <div className="bg-card text-card-foreground border border-border rounded-lg">
                      <div className="border-b border-border p-4">
                        <h4 className="text-lg font-semibold text-foreground">Player Details</h4>
                        <p className="text-sm text-muted-foreground mt-1">Click on a player's values to edit them</p>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="min-w-full">
                          <thead className="bg-card border-b border-border rounded-t-lg">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Player</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Buy-in</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Cash-out</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">In Game</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Net</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider rounded-tr-lg">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="bg-card">
                            {sessionDetail.players.map((player, _index) => {
                              const isEditing = editingPlayer === player.player_id;
                              const playerEditValues = editValues[player.player_id];
                              
                              return (
                                <tr key={player.player_id} className="border-b border-border hover:bg-accent/50">
                                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                                    {player.display_name}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                                    {isEditing ? (
                                      <input
                                        type="text"
                                        value={playerEditValues?.buy_in || ''}
                                        onChange={(e) => setEditValues({
                                          ...editValues,
                                          [player.player_id]: {
                                            ...playerEditValues!,
                                            buy_in: e.target.value
                                          }
                                        })}
                                        className="w-20 px-2 py-1 text-right border border-input rounded text-sm bg-background"
                                      />
                                    ) : (
                                      <span className="cursor-pointer hover:bg-warning/20 px-2 py-1 rounded" onClick={() => startEditingPlayer(player.player_id, player)}>
                                        ${formatCurrency(player.buy_in_sum)}
                                      </span>
                                    )}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                                    {isEditing ? (
                                      <input
                                        type="text"
                                        value={playerEditValues?.cash_out || ''}
                                        onChange={(e) => setEditValues({
                                          ...editValues,
                                          [player.player_id]: {
                                            ...playerEditValues!,
                                            cash_out: e.target.value
                                          }
                                        })}
                                        className="w-20 px-2 py-1 text-right border border-input rounded text-sm bg-background"
                                      />
                                    ) : (
                                      <span className="cursor-pointer hover:bg-warning/20 px-2 py-1 rounded" onClick={() => startEditingPlayer(player.player_id, player)}>
                                        ${formatCurrency(player.cash_out_sum)}
                                      </span>
                                    )}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                                    {isEditing ? (
                                      <input
                                        type="text"
                                        value={playerEditValues?.in_game || ''}
                                        onChange={(e) => setEditValues({
                                          ...editValues,
                                          [player.player_id]: {
                                            ...playerEditValues!,
                                            in_game: e.target.value
                                          }
                                        })}
                                        className="w-20 px-2 py-1 text-right border border-input rounded text-sm bg-background"
                                      />
                                    ) : (
                                      <span className="cursor-pointer hover:bg-warning/20 px-2 py-1 rounded" onClick={() => startEditingPlayer(player.player_id, player)}>
                                        ${formatCurrency(player.in_game)}
                                      </span>
                                    )}
                                  </td>
                                  <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium text-right ${
                                    player.net > 0 ? 'text-success' : player.net < 0 ? 'text-destructive' : 'text-foreground'
                                  }`}>
                                    {isEditing && playerEditValues ? (
                                      <span className="text-muted-foreground">
                                        ${((parseFloat(playerEditValues.cash_out || '0') + parseFloat(playerEditValues.in_game || '0')) - parseFloat(playerEditValues.buy_in || '0')).toFixed(2)}
                                      </span>
                                    ) : (
                                      `$${formatCurrency(player.net)}`
                                    )}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    {isEditing ? (
                                      <div className="space-x-2">
                                        <button
                                          onClick={() => savePlayerChanges(player.player_id)}
                                          className="text-success hover:text-success/80"
                                        >
                                          Save
                                        </button>
                                        <button
                                          onClick={() => cancelEditing(player.player_id)}
                                          className="text-muted-foreground hover:text-foreground"
                                        >
                                          Cancel
                                        </button>
                                      </div>
                                    ) : (
                                      <div className="space-x-2">
                                        <button
                                          onClick={() => startEditingPlayer(player.player_id, player)}
                                          className="text-primary hover:text-primary/80"
                                        >
                                          Edit
                                        </button>
                                        <button
                                          onClick={() => {
                                            setDeleteTarget({
                                              sessionId: selectedSessionId!,
                                              playerId: player.player_id,
                                              playerName: player.display_name
                                            });
                                            setShowDeleteModal(true);
                                          }}
                                          className="text-destructive hover:text-destructive/80"
                                        >
                                          Delete
                                        </button>
                                      </div>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Audit Logs */}
                    {sessionDetail.audit_logs && sessionDetail.audit_logs.length > 0 && (
                      <div className="bg-card text-card-foreground border border-border rounded-lg">
                        <div className="border-b border-border p-4">
                          <h4 className="text-lg font-semibold text-foreground">Audit Log</h4>
                        </div>
                        <div className="max-h-64 overflow-y-auto">
                          <div className="space-y-2 p-4">
                            {sessionDetail.audit_logs.map((audit) => (
                              <div key={audit.id} className="border border-border rounded p-3">
                                <div className="flex items-center justify-between">
                                  <div className="text-sm font-medium text-foreground">
                                    {audit.action} on {audit.target_table}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    {formatDate(audit.timestamp)}
                                  </div>
                                </div>
                                <div className="text-sm text-muted-foreground mt-1">
                                  {audit.description}
                                </div>
                                <button
                                  onClick={() => setExpandedAuditId(expandedAuditId === audit.id ? null : audit.id)}
                                  className="text-xs text-primary hover:text-primary/80 mt-2"
                                >
                                  {expandedAuditId === audit.id ? 'Hide Details' : 'Show Details'}
                                </button>
                                {expandedAuditId === audit.id && (
                                  <div className="mt-2 text-xs bg-accent p-2 rounded border border-border">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                      <div>
                                        <div className="font-medium text-foreground mb-1">Before:</div>
                                        <pre className="text-xs text-muted-foreground overflow-auto">
                                          {JSON.stringify(audit.before, null, 2)}
                                        </pre>
                                      </div>
                                      <div>
                                        <div className="font-medium text-foreground mb-1">After:</div>
                                        <pre className="text-xs text-muted-foreground overflow-auto">
                                          {JSON.stringify(audit.after, null, 2)}
                                        </pre>
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                  </div>
                ) : (
                  <div className="text-center text-destructive py-8">Failed to load session details</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Delete Player Confirmation Modal */}
        {showDeleteModal && deleteTarget && (
          <div className="fixed inset-0 bg-black bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border border-border w-96 shadow-lg rounded-md bg-card text-card-foreground">
              <div className="mt-3 text-center">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-destructive/10">
                  <svg className="h-6 w-6 text-destructive" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L3.354 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <h3 className="text-lg leading-6 font-medium text-foreground mt-2">Delete Player</h3>
                <div className="mt-2 px-7 py-3">
                  <p className="text-sm text-muted-foreground">
                    Are you sure you want to delete <strong>{deleteTarget.playerName}</strong> from this session? 
                    This action cannot be undone and will permanently remove all their data from this session.
                  </p>
                </div>
                <div className="items-center px-4 py-3">
                  <div className="flex space-x-2">
                    <button
                      onClick={() => {
                        setShowDeleteModal(false);
                        setDeleteTarget(null);
                      }}
                      className="flex-1 px-4 py-2 bg-secondary text-secondary-foreground text-base font-medium rounded-md shadow-sm hover:bg-secondary/80 focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => deletePlayer(deleteTarget.sessionId, deleteTarget.playerId)}
                      className="flex-1 px-4 py-2 bg-destructive text-destructive-foreground text-base font-medium rounded-2xl shadow-sm hover:bg-destructive/90 focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      Delete Player
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Add Player Modal */}
        {showAddPlayerModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border border-border w-96 shadow-lg rounded-md bg-card text-card-foreground">
              <div className="flex items-center justify-between border-b pb-3 mb-4">
                <h3 className="text-lg font-semibold text-foreground">Add Player to Session</h3>
                <button
                  onClick={() => {
                    setShowAddPlayerModal(false);
                    setNewPlayerData({
                      playerName: '',
                      buyInSum: '',
                      cashOutSum: '',
                      inGame: ''
                    });
                  }}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label htmlFor="playerName" className="block text-sm font-medium text-foreground">Player Name</label>
                  <input
                    type="text"
                    id="playerName"
                    value={newPlayerData.playerName}
                    onChange={(e) => setNewPlayerData({...newPlayerData, playerName: e.target.value})}
                    className="mt-1 block w-full px-3 py-2 border border-input rounded-md shadow-sm bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                    placeholder="Enter player name"
                    required
                  />
                </div>
                
                <div>
                  <label htmlFor="buyInSum" className="block text-sm font-medium text-foreground">Buy In Amount</label>
                  <input
                    type="number"
                    id="buyInSum"
                    value={newPlayerData.buyInSum}
                    onChange={(e) => setNewPlayerData({...newPlayerData, buyInSum: e.target.value})}
                    className="mt-1 block w-full px-3 py-2 border border-input rounded-md shadow-sm bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                    placeholder="0.00"
                    min="0"
                    step="0.01"
                    required
                  />
                </div>
                
                <div>
                  <label htmlFor="cashOutSum" className="block text-sm font-medium text-foreground">Cash Out Amount</label>
                  <input
                    type="number"
                    id="cashOutSum"
                    value={newPlayerData.cashOutSum}
                    onChange={(e) => setNewPlayerData({...newPlayerData, cashOutSum: e.target.value})}
                    className="mt-1 block w-full px-3 py-2 border border-input rounded-md shadow-sm bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                    placeholder="0.00"
                    min="0"
                    step="0.01"
                  />
                </div>
                
                <div>
                  <label htmlFor="inGame" className="block text-sm font-medium text-foreground">In Game Amount</label>
                  <input
                    type="number"
                    id="inGame"
                    value={newPlayerData.inGame}
                    onChange={(e) => setNewPlayerData({...newPlayerData, inGame: e.target.value})}
                    className="mt-1 block w-full px-3 py-2 border border-input rounded-md shadow-sm bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                    placeholder="0.00"
                    min="0"
                    step="0.01"
                  />
                </div>
              </div>
              
              <div className="mt-6 flex space-x-2">
                <button
                  onClick={() => {
                    setShowAddPlayerModal(false);
                    setNewPlayerData({
                      playerName: '',
                      buyInSum: '',
                      cashOutSum: '',
                      inGame: ''
                    });
                  }}
                  className="flex-1 px-4 py-2 bg-secondary text-secondary-foreground text-base font-medium rounded-md shadow-sm hover:bg-secondary/80 focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  Cancel
                </button>
                <button
                  onClick={addPlayerToSession}
                  disabled={!newPlayerData.playerName || !newPlayerData.buyInSum}
                  className="flex-1 px-4 py-2 bg-black text-white text-base font-medium rounded-2xl shadow-sm hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add Player
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}