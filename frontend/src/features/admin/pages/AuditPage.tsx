import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useToast } from '../../../contexts/ToastContext';
import { Pagination } from '../../../shared/ui/pagination';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';

interface AuditEntry {
  id: string;
  game_id: string | null;
  session_id: string | null;
  actor_kind: string;
  actor_id: string;
  action: string;
  target_table: string;
  target_id: string;
  timestamp: string;
  before: any;
  after: any;
  can_undo: boolean;
  description: string;
}

interface AuditData {
  audit_logs: AuditEntry[];
  total_count: number;
  page_size: number;
  offset: number;
}

interface OperationDetails {
  operation_id: string;
  action: string;
  timestamp: string;
  actor: string;
  before_state: any;
  after_state: any;
  can_undo: boolean;
}

export default function AuditPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const { adminCode: sessionAdminCode, hasAdminSession } = useAdminSession();
  const { showSuccess, showError } = useToast();
  const { title } = useGameTitle(publicCode || '');
  const [auditData, setAuditData] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedOperation, setSelectedOperation] = useState<OperationDetails | null>(null);
  const [showUndoConfirm, setShowUndoConfirm] = useState(false);
  const [manualAdminCode, setManualAdminCode] = useState('');
  const [showAdminInput, setShowAdminInput] = useState(false);
  const [undoLoading, setUndoLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 25; // 25 items per page
  
  // Use session admin code if available, otherwise manual input
  const effectiveAdminCode = sessionAdminCode || manualAdminCode;

  useEffect(() => {
    if (publicCode) {
      fetchAuditData(1);
      setCurrentPage(1);
    }
  }, [publicCode]);

  const handlePageChange = async (page: number) => {
    setCurrentPage(page);
    await fetchAuditData(page);
  };

  const fetchAuditData = async (page: number = currentPage) => {
    try {
      setLoading(true);
      const offset = (page - 1) * itemsPerPage;
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/audit?limit=${itemsPerPage}&offset=${offset}`);
      setAuditData(response.data);
    } catch (error) {
      console.error('Error fetching audit data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = async (operationId: string) => {
    try {
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/audit/operation/${operationId}`);
      setSelectedOperation(response.data);
      setShowDetailsModal(true);
    } catch (error) {
      console.error('Error fetching operation details:', error);
      showError('Load Failed', 'Failed to load operation details');
    }
  };

  const handleUndoClick = (entry: AuditEntry) => {
    if (!entry.can_undo) return;
    setSelectedOperation({
      operation_id: entry.target_id,
      action: entry.action,
      timestamp: entry.timestamp,
      actor: entry.actor_id,
      before_state: entry.before,
      after_state: entry.after,
      can_undo: entry.can_undo
    });
    setShowUndoConfirm(true);
  };

  const executeUndo = async () => {
    if (!selectedOperation || !effectiveAdminCode.trim()) {
      setShowAdminInput(true);
      return;
    }

    try {
      setUndoLoading(true);
      await axios.post(
        `http://localhost:8000/api/games/${publicCode}/audit/undo/${selectedOperation.operation_id}`,
        {},
        { headers: { 'X-Admin-Code': effectiveAdminCode } }
      );

      showSuccess('Undo Successful', 'Operation successfully undone!');
      setShowUndoConfirm(false);
      setShowAdminInput(false);
      setSelectedOperation(null);
      setManualAdminCode('');
      fetchAuditData(); // Refresh the audit log
    } catch (error) {
      console.error('Error undoing operation:', error);
      showError('Undo Failed', 'Failed to undo operation. Please check your admin code.');
    } finally {
      setUndoLoading(false);
    }
  };

  const handleCancel = () => {
    setShowDetailsModal(false);
    setShowUndoConfirm(false);
    setShowAdminInput(false);
    setSelectedOperation(null);
    setManualAdminCode('');
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const renderPlayerInfo = (playerData: any, title: string) => {
    if (!playerData) return null;
    
    return (
      <div className="mb-4">
        <h4 className="font-medium text-gray-900 mb-2">{title}</h4>
        <div className="bg-gray-50 p-3 rounded">
          <div><strong>Name:</strong> {playerData.display_name}</div>
          <div><strong>External ID:</strong> {playerData.external_id || 'None'}</div>
          <div><strong>Sessions:</strong> {playerData.sessions?.length || 0}</div>
          {playerData.sessions && playerData.sessions.length > 0 && (
            <div className="mt-2">
              <strong>Session Details:</strong>
              <div className="max-h-32 overflow-y-auto mt-1">
                {playerData.sessions.map((session: any, idx: number) => (
                  <div key={idx} className="text-sm text-gray-600 border-b pb-1 mb-1">
                    Session {session.session_external_id || session.session_id}: 
                    Buy-in: ${(session.buy_in_sum / 100).toFixed(2)}, 
                    Cash-out: ${(session.cash_out_sum / 100).toFixed(2)}, 
                    Net: ${(session.net / 100).toFixed(2)}
                    {session.names && ` (${session.names.join(', ')})`}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderGenericData = (data: any, title: string) => {
    if (!data) return null;

    const formatValue = (key: string, value: any) => {
      if (key.includes('sum') && typeof value === 'number') {
        return `$${(value / 100).toFixed(2)}`;
      }
      if (Array.isArray(value)) {
        return value.join(', ');
      }
      if (typeof value === 'object' && value !== null) {
        return JSON.stringify(value, null, 2);
      }
      return String(value);
    };

    return (
      <div className="mb-4">
        <h4 className="font-medium text-gray-900 mb-2">{title}</h4>
        <div className="bg-gray-50 p-3 rounded">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="mb-1">
              <strong className="capitalize">{key.replace(/_/g, ' ')}:</strong> {formatValue(key, value)}
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-6xl mx-auto px-4">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Audit Log</h1>
            <p className="mt-2 text-gray-600">
              Game <span className="font-mono bg-gray-100 px-2 py-1 rounded">{title}</span>
            </p>
          </div>
          <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
            Loading audit data...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Audit Log</h1>
            <p className="mt-2 text-gray-600">
              Database operations for game <span className="font-mono bg-gray-100 px-2 py-1 rounded">{title}</span>
            </p>
          </div>
          <button
            onClick={() => fetchAuditData(currentPage)}
            className="px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Refresh
          </button>
        </div>

      <div className="bg-white rounded-lg border shadow-sm">
        <div className="border-b p-4">
          <h3 className="text-lg font-semibold">All Database Operations</h3>
          <p className="text-sm text-gray-600 mt-1">
            {auditData?.total_count || 0} operations found
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {auditData?.audit_logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    No audit entries found
                  </td>
                </tr>
              ) : (
                auditData?.audit_logs.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatTimestamp(entry.timestamp)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        entry.action === 'PLAYER_MERGE' 
                          ? 'bg-blue-100 text-blue-800'
                          : entry.action === 'PLAYER_MERGE_UNDO'
                          ? 'bg-green-100 text-green-800'
                          : entry.action.includes('VERIFY')
                          ? 'bg-purple-100 text-purple-800'
                          : entry.action.includes('UPDATE')
                          ? 'bg-yellow-100 text-yellow-800'
                          : entry.action.includes('INSERT')
                          ? 'bg-green-100 text-green-800'
                          : entry.action.includes('DELETE')
                          ? 'bg-red-100 text-red-800'
                          : entry.action.includes('IMPORT')
                          ? 'bg-indigo-100 text-indigo-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {entry.action.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {entry.actor_id}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {entry.description || 'No description available'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                      <button
                        onClick={() => handleViewDetails(entry.id)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        View Details
                      </button>
                      {entry.can_undo && (
                        <button
                          onClick={() => handleUndoClick(entry)}
                          className="text-red-600 hover:text-red-900 ml-3"
                        >
                          Undo
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {auditData && auditData.total_count > itemsPerPage && (
          <Pagination
            currentPage={currentPage}
            totalPages={Math.ceil(auditData.total_count / itemsPerPage)}
            onPageChange={handlePageChange}
            itemsPerPage={itemsPerPage}
            totalItems={auditData.total_count}
          />
        )}
      </div>

      {/* Details Modal */}
      {showDetailsModal && selectedOperation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-4xl my-8">
            <h3 className="text-lg font-medium text-gray-900 mb-6">
              Operation Details
            </h3>
            
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><strong>Operation ID:</strong> {selectedOperation.operation_id}</div>
                <div><strong>Action:</strong> {selectedOperation.action}</div>
                <div><strong>Timestamp:</strong> {formatTimestamp(selectedOperation.timestamp)}</div>
                <div><strong>Actor:</strong> {selectedOperation.actor}</div>
              </div>

              {selectedOperation.before_state && (
                <div>
                  {selectedOperation.action === 'PLAYER_MERGE' ? (
                    // Render player merge data structure
                    <div>
                      <h4 className="font-medium text-gray-900 mb-4">Before State</h4>
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {renderPlayerInfo(selectedOperation.before_state.target_player, "Target Player")}
                        <div>
                          <h5 className="font-medium text-gray-900 mb-2">Source Players</h5>
                          {selectedOperation.before_state.source_players?.map((player: any, idx: number) => (
                            <div key={idx} className="mb-3">
                              {renderPlayerInfo(player, `Source Player ${idx + 1}`)}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    // Render generic data structure for other operations
                    renderGenericData(selectedOperation.before_state, "Before State")
                  )}
                </div>
              )}

              {selectedOperation.after_state && (
                <div>
                  {selectedOperation.action === 'PLAYER_MERGE' ? (
                    // Render player merge data structure
                    <div>
                      <h4 className="font-medium text-gray-900 mb-4">After State</h4>
                      {renderPlayerInfo(selectedOperation.after_state.target_player, "Merged Player")}
                    </div>
                  ) : (
                    // Render generic data structure for other operations
                    renderGenericData(selectedOperation.after_state, "After State")
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Undo Confirmation Modal */}
      {showUndoConfirm && selectedOperation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Confirm Undo Operation
            </h3>
            
            <p className="text-sm text-gray-600 mb-4">
              This will undo the merge operation and restore all players to their original state. 
              This action cannot be undone.
            </p>

            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
              <div className="text-sm text-yellow-800">
                <strong>Operation:</strong> {selectedOperation.action}<br/>
                <strong>Date:</strong> {formatTimestamp(selectedOperation.timestamp)}<br/>
                <strong>Players affected:</strong> {selectedOperation.before_state?.source_players?.length + 1}
              </div>
            </div>

            {(showAdminInput && !hasAdminSession) && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Admin Code *
                </label>
                <input
                  type="password"
                  value={manualAdminCode}
                  onChange={(e) => setManualAdminCode(e.target.value)}
                  placeholder="Enter admin code..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                />
              </div>
            )}
            
            {hasAdminSession && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="text-sm text-green-800">
                  <strong>Using stored admin session</strong><br/>
                  Game: {publicCode}<br/>
                  Admin code is automatically applied for this session.
                </div>
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={handleCancel}
                disabled={undoLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={executeUndo}
                disabled={undoLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {undoLoading ? 'Undoing...' : 'Confirm Undo'}
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}