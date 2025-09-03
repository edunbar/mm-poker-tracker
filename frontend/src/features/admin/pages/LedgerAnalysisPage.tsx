import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import AdminSessionStatus from '../../../components/AdminSessionStatus';

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
  const [loading, setLoading] = useState(false);
  const [sessionAnalysis, setSessionAnalysis] = useState<SessionAnalysis[]>([]);
  const [mathErrors, setMathErrors] = useState<MathError[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [expandedAuditId, setExpandedAuditId] = useState<string | null>(null);

  useEffect(() => {
    if (publicCode) {
      fetchAnalysisData();
    }
  }, [publicCode]);

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
      console.error('Error fetching analysis data:', error);
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
      console.error('Error fetching session detail:', error);
    } finally {
      setSessionLoading(false);
    }
  };

  const closeSessionModal = () => {
    setSelectedSessionId(null);
    setSessionDetail(null);
    setExpandedAuditId(null);
  };

  const formatCurrency = (amount: number) => {
    return (amount / 100).toFixed(2);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  if (!hasAdminSession) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-6xl mx-auto px-4">
          <AdminSessionStatus />
          <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
            <p className="text-lg text-gray-600">Please log in with admin credentials to view ledger analysis.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <AdminSessionStatus />
        
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Game Ledger Analysis</h1>
          <p className="mt-2 text-gray-600">
            Analyze session balances and identify data issues for game <span className="font-mono bg-gray-100 px-2 py-1 rounded">{publicCode}</span>
          </p>
        </div>
          
        {loading ? (
          <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Analyzing game data...</p>
          </div>
        ) : sessionAnalysis.length === 0 && mathErrors.length === 0 ? (
          <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
            <div className="text-green-600 text-6xl mb-4">✓</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">All Sessions Balanced</h3>
            <p className="text-gray-600">No ledger issues detected in this game.</p>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Unbalanced Sessions Section */}
            {sessionAnalysis.length > 0 && (
              <div className="bg-white rounded-lg border shadow-sm">
                <div className="border-b p-4">
                  <h3 className="text-lg font-semibold">Unbalanced Sessions</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Sessions where total buy-ins don't equal total cash-outs plus in-game chips
                  </p>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-red-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-red-700 uppercase tracking-wider">Game #</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-red-700 uppercase tracking-wider">External ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-red-700 uppercase tracking-wider">Started</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-red-700 uppercase tracking-wider">Players</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Buy-ins</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Cash-outs</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">In Game</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Balance</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {sessionAnalysis.map((session) => (
                        <tr key={session.session_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            #{session.game_number}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                            {session.external_id}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(session.started_at)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {session.player_count}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${formatCurrency(session.buy_ins)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${formatCurrency(session.cash_outs)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${formatCurrency(session.in_game)}
                          </td>
                          <td className={`px-6 py-4 whitespace-nowrap text-sm font-bold text-right ${
                            session.balance > 0 ? 'text-red-600' : 'text-blue-600'
                          }`}>
                            ${formatCurrency(Math.abs(session.balance))} {session.balance > 0 ? 'over' : 'under'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => openSessionModal(session.session_id)}
                              className="text-blue-600 hover:text-blue-900"
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
              <div className="bg-white rounded-lg border shadow-sm">
                <div className="border-b p-4">
                  <h3 className="text-lg font-semibold">Individual Math Errors</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Player entries where recorded net doesn't match calculated net (cash-out + in-game - buy-in)
                  </p>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-red-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-red-700 uppercase tracking-wider">Game #</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-red-700 uppercase tracking-wider">Player</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Buy-in</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Cash-out</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">In Game</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Recorded Net</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Calculated Net</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Difference</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-red-700 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {mathErrors.map((error) => (
                        <tr key={`${error.session_id}-${error.player_id}`} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            #{error.game_number}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">{error.player_name}</div>
                            <div className="text-sm text-gray-500">
                              {error.names.length > 1 && `(${error.names.join(', ')})`}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${formatCurrency(error.buy_in)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${formatCurrency(error.cash_out)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${formatCurrency(error.in_game)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${formatCurrency(error.recorded_net)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 text-right font-medium">
                            ${formatCurrency(error.calculated_net)}
                          </td>
                          <td className={`px-6 py-4 whitespace-nowrap text-sm font-bold text-right ${
                            error.difference > 0 ? 'text-red-600' : 'text-blue-600'
                          }`}>
                            ${formatCurrency(Math.abs(error.difference))} {error.difference > 0 ? 'over' : 'under'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => openSessionModal(error.session_id)}
                              className="text-blue-600 hover:text-blue-900"
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
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-40">
            <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-6xl shadow-lg rounded-md bg-white">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="text-2xl font-semibold text-gray-900">Session Details</h3>
                <button
                  onClick={closeSessionModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mt-4">
                {sessionLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                  </div>
                ) : sessionDetail ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-500">Game Number</div>
                        <div className="text-lg font-semibold">#{sessionDetail.game_number}</div>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-500">External ID</div>
                        <div className="text-lg font-mono">{sessionDetail.external_id}</div>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-500">Started At</div>
                        <div className="text-lg">{formatDate(sessionDetail.started_at)}</div>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-500">Players</div>
                        <div className="text-lg font-semibold">{sessionDetail.players.length}</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <div className="text-sm text-blue-600">Total Buy-ins</div>
                        <div className="text-xl font-bold text-blue-700">${formatCurrency(sessionDetail.totals.buy_ins)}</div>
                      </div>
                      <div className="bg-green-50 p-4 rounded-lg">
                        <div className="text-sm text-green-600">Total Cash-outs</div>
                        <div className="text-xl font-bold text-green-700">${formatCurrency(sessionDetail.totals.cash_outs)}</div>
                      </div>
                      <div className="bg-yellow-50 p-4 rounded-lg">
                        <div className="text-sm text-yellow-600">Total In Game</div>
                        <div className="text-xl font-bold text-yellow-700">${formatCurrency(sessionDetail.totals.in_game)}</div>
                      </div>
                      <div className={`p-4 rounded-lg ${sessionDetail.totals.balance === 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                        <div className={`text-sm ${sessionDetail.totals.balance === 0 ? 'text-green-600' : 'text-red-600'}`}>Balance</div>
                        <div className={`text-xl font-bold ${sessionDetail.totals.balance === 0 ? 'text-green-700' : 'text-red-700'}`}>
                          ${formatCurrency(Math.abs(sessionDetail.totals.balance))} {sessionDetail.totals.balance > 0 ? 'over' : sessionDetail.totals.balance < 0 ? 'under' : 'balanced'}
                        </div>
                      </div>
                    </div>

                    {/* Player Details */}
                    <div className="bg-white border rounded-lg">
                      <div className="border-b p-4">
                        <h4 className="text-lg font-semibold">Player Details</h4>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Player</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Buy-in</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Cash-out</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">In Game</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Net</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {sessionDetail.players.map((player, index) => (
                              <tr key={player.player_id} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                  {player.display_name}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                                  ${formatCurrency(player.buy_in_sum)}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                                  ${formatCurrency(player.cash_out_sum)}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                                  ${formatCurrency(player.in_game)}
                                </td>
                                <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium text-right ${
                                  player.net > 0 ? 'text-green-600' : player.net < 0 ? 'text-red-600' : 'text-gray-900'
                                }`}>
                                  ${formatCurrency(player.net)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Audit Logs */}
                    {sessionDetail.audit_logs && sessionDetail.audit_logs.length > 0 && (
                      <div className="bg-white border rounded-lg">
                        <div className="border-b p-4">
                          <h4 className="text-lg font-semibold">Audit Log</h4>
                        </div>
                        <div className="max-h-64 overflow-y-auto">
                          <div className="space-y-2 p-4">
                            {sessionDetail.audit_logs.map((audit) => (
                              <div key={audit.id} className="border rounded p-3">
                                <div className="flex items-center justify-between">
                                  <div className="text-sm font-medium text-gray-900">
                                    {audit.action} on {audit.target_table}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {formatDate(audit.timestamp)}
                                  </div>
                                </div>
                                <div className="text-sm text-gray-600 mt-1">
                                  {audit.description}
                                </div>
                                <button
                                  onClick={() => setExpandedAuditId(expandedAuditId === audit.id ? null : audit.id)}
                                  className="text-xs text-blue-600 hover:text-blue-800 mt-2"
                                >
                                  {expandedAuditId === audit.id ? 'Hide Details' : 'Show Details'}
                                </button>
                                {expandedAuditId === audit.id && (
                                  <div className="mt-2 text-xs bg-gray-50 p-2 rounded">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                      <div>
                                        <div className="font-medium text-gray-700 mb-1">Before:</div>
                                        <pre className="text-xs text-gray-600 overflow-auto">
                                          {JSON.stringify(audit.before, null, 2)}
                                        </pre>
                                      </div>
                                      <div>
                                        <div className="font-medium text-gray-700 mb-1">After:</div>
                                        <pre className="text-xs text-gray-600 overflow-auto">
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

                    {/* Data Comparison */}
                    {sessionDetail.data_comparison && (
                      <div className="bg-white border rounded-lg">
                        <div className="border-b p-4">
                          <h4 className="text-lg font-semibold">Data Comparison</h4>
                          {sessionDetail.data_comparison.has_differences ? (
                            <p className="text-sm text-red-600 mt-1">
                              Differences detected between original and current data
                            </p>
                          ) : (
                            <p className="text-sm text-green-600 mt-1">
                              No differences detected
                            </p>
                          )}
                        </div>
                        <div className="p-4 space-y-4">
                          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                            <div>
                              <div className="text-gray-500">Original Players</div>
                              <div className="font-semibold">{sessionDetail.data_comparison.summary.original_player_count}</div>
                            </div>
                            <div>
                              <div className="text-gray-500">Current Players</div>
                              <div className="font-semibold">{sessionDetail.data_comparison.summary.current_player_count}</div>
                            </div>
                            <div>
                              <div className="text-gray-500">Missing</div>
                              <div className="font-semibold text-red-600">{sessionDetail.data_comparison.summary.missing_count}</div>
                            </div>
                            <div>
                              <div className="text-gray-500">Added</div>
                              <div className="font-semibold text-blue-600">{sessionDetail.data_comparison.summary.added_count}</div>
                            </div>
                            <div>
                              <div className="text-gray-500">Modified</div>
                              <div className="font-semibold text-yellow-600">{sessionDetail.data_comparison.summary.modified_count}</div>
                            </div>
                          </div>

                          {sessionDetail.data_comparison.missing_players.length > 0 && (
                            <div>
                              <h5 className="font-medium text-red-600 mb-2">Missing Players</h5>
                              {sessionDetail.data_comparison.missing_players.map((player, index) => (
                                <div key={index} className="text-sm bg-red-50 p-2 rounded mb-1">
                                  {player.name}
                                </div>
                              ))}
                            </div>
                          )}

                          {sessionDetail.data_comparison.added_players.length > 0 && (
                            <div>
                              <h5 className="font-medium text-blue-600 mb-2">Added Players</h5>
                              {sessionDetail.data_comparison.added_players.map((player, index) => (
                                <div key={index} className="text-sm bg-blue-50 p-2 rounded mb-1">
                                  {player.name}
                                </div>
                              ))}
                            </div>
                          )}

                          {sessionDetail.data_comparison.modified_players.length > 0 && (
                            <div>
                              <h5 className="font-medium text-yellow-600 mb-2">Modified Players</h5>
                              {sessionDetail.data_comparison.modified_players.map((player, index) => (
                                <div key={index} className="text-sm bg-yellow-50 p-2 rounded mb-1">
                                  <div className="font-medium">{player.name}</div>
                                  <div className="text-xs text-gray-600 mt-1">
                                    <pre>{JSON.stringify(player.differences, null, 2)}</pre>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {sessionDetail.data_comparison.error && (
                            <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                              Error: {sessionDetail.data_comparison.error}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-red-600 py-8">Failed to load session details</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}