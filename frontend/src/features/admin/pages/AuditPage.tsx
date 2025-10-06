import axios from 'axios';
import { useCallback, useEffect, useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { API_BASE_URL } from '../../../config/api';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useToast } from '../../../contexts/ToastContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';
import { Button } from '../../../shared/ui/button';
import { EnhancedDataTable, createColumn } from '../../../shared/ui/enhanced-data-table';
import { Pagination } from '../../../shared/ui/pagination';
import { Heading, Text } from '../../../shared/ui/typography';

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
  before: unknown;
  after: unknown;
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
  before_state: unknown;
  after_state: unknown;
  can_undo: boolean;
}

export default function AuditPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const { getAdminCode, hasAdminSession: hasAdminSessionForGame } = useAdminSession();
  const sessionAdminCode = getAdminCode(publicCode || '');
  const hasAdminSession = hasAdminSessionForGame(publicCode || '');
  const { showSuccess, showError } = useToast();
  const { title: _title } = useGameTitle(publicCode || '');
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

  const fetchAuditData = useCallback(async (page: number) => {
    try {
      setLoading(true);
      const offset = (page - 1) * itemsPerPage;
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/audit?limit=${itemsPerPage}&offset=${offset}`);
      setAuditData(response.data);
    } catch (error) {
      // Silently handle error
    } finally {
      setLoading(false);
    }
  }, [publicCode, itemsPerPage]);

  useEffect(() => {
    if (publicCode) {
      fetchAuditData(1);
      setCurrentPage(1);
    }
  }, [publicCode, fetchAuditData]);

  const handlePageChange = async (page: number) => {
    setCurrentPage(page);
    await fetchAuditData(page);
  };

  const handleViewDetails = useCallback(async (operationId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/audit/operation/${operationId}`);
      setSelectedOperation(response.data);
      setShowDetailsModal(true);
    } catch (error) {
      showError('Load Failed', 'Failed to load operation details');
    }
  }, [publicCode, showError]);

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
        `${API_BASE_URL}/api/games/${publicCode}/audit/undo/${selectedOperation.operation_id}`,
        {},
        { headers: { 'X-Admin-Code': effectiveAdminCode } }
      );

      showSuccess('Undo Successful', 'Operation successfully undone!');
      setShowUndoConfirm(false);
      setShowAdminInput(false);
      setSelectedOperation(null);
      setManualAdminCode('');
      fetchAuditData(currentPage); // Refresh the audit log
    } catch (error) {
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

  const auditColumns = useMemo(() => [
    createColumn('timestamp', 'Timestamp', (entry: AuditEntry) => (
      <span className="text-sm text-foreground whitespace-nowrap">
        {formatTimestamp(entry.timestamp)}
      </span>
    ), {
      sortable: true,
      className: 'w-48'
    }),
    createColumn('action', 'Action', (entry: AuditEntry) => (
      <span className={`px-2 py-1 text-xs font-medium rounded-full whitespace-nowrap ${
        entry.action === 'PLAYER_MERGE'
          ? 'bg-primary/10 text-primary'
          : entry.action === 'PLAYER_MERGE_UNDO'
          ? 'bg-success/10 text-success'
          : entry.action.includes('VERIFY')
          ? 'bg-info/10 text-info'
          : entry.action.includes('UPDATE')
          ? 'bg-warning/10 text-warning'
          : entry.action.includes('INSERT')
          ? 'bg-success/10 text-success'
          : entry.action.includes('DELETE')
          ? 'bg-destructive/10 text-destructive'
          : entry.action.includes('IMPORT')
          ? 'bg-primary/10 text-primary'
          : 'bg-muted text-muted-foreground'
      }`}>
        {entry.action.replace('_', ' ')}
      </span>
    ), {
      sortable: true,
      className: 'w-32'
    }),
    createColumn('actor', 'Actor', (entry: AuditEntry) => (
      <span className="text-sm text-muted-foreground whitespace-nowrap">
        {entry.actor_id}
      </span>
    ), {
      sortable: true,
      className: 'w-32'
    }),
    createColumn('details', 'Details', (entry: AuditEntry) => (
      <span className="text-sm text-muted-foreground">
        {entry.description || 'No description available'}
      </span>
    ), {
      className: 'flex-1'
    }),
    createColumn('actions', 'Actions', (entry: AuditEntry) => (
      <div className="flex space-x-2 text-sm font-medium">
        <Button
          onClick={() => handleViewDetails(entry.id)}
          variant="ghost"
          size="sm"
          className="text-primary hover:text-primary/80 p-0 h-auto"
        >
          View Details
        </Button>
        {entry.can_undo && (
          <Button
            onClick={() => handleUndoClick(entry)}
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive/80 p-0 h-auto"
          >
            Undo
          </Button>
        )}
      </div>
    ), {
      className: 'w-48'
    }),
  ], [handleViewDetails]);

  const renderPlayerInfo = (playerData: unknown, title: string) => {
    if (!playerData || typeof playerData !== 'object') return null;

    const data = playerData as Record<string, unknown>;
    const sessions = Array.isArray(data.sessions) ? data.sessions : [];

    return (
      <div className="mb-4">
        <Text variant="body" weight="medium" as="h4" className="mb-2">{title}</Text>
        <div className="bg-muted p-3 rounded">
          <div><strong>Name:</strong> {String(data.display_name || '')}</div>
          <div><strong>External ID:</strong> {String(data.external_id || 'None')}</div>
          <div><strong>Sessions:</strong> {sessions.length}</div>
          {sessions.length > 0 && (
            <div className="mt-2">
              <strong>Session Details:</strong>
              <div className="max-h-32 overflow-y-auto mt-1">
                {sessions.map((session: unknown, idx: number) => {
                  const sess = session as Record<string, unknown>;
                  const buyIn = typeof sess.buy_in_sum === 'number' ? sess.buy_in_sum : 0;
                  const cashOut = typeof sess.cash_out_sum === 'number' ? sess.cash_out_sum : 0;
                  const net = typeof sess.net === 'number' ? sess.net : 0;
                  const names = Array.isArray(sess.names) ? sess.names : [];
                  return (
                  <div key={idx} className="text-sm text-muted-foreground border-b border-border pb-1 mb-1">
                    Session {String(sess.session_external_id || sess.session_id || '')}:
                    Buy-in: ${(buyIn / 100).toFixed(2)},
                    Cash-out: ${(cashOut / 100).toFixed(2)},
                    Net: ${(net / 100).toFixed(2)}
                    {names.length > 0 && ` (${names.join(', ')})`}
                  </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderGenericData = (data: unknown, title: string) => {
    if (!data || typeof data !== 'object') return null;

    const formatValue = (key: string, value: unknown): string => {
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
        <Text variant="body" weight="medium" as="h4" className="mb-2">{title}</Text>
        <div className="bg-muted p-3 rounded">
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
      <div className="min-h-screen bg-background py-8">
        <div className="max-w-6xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="mb-8">
            <Heading variant="h1">Audit Log</Heading>
            <Text variant="body" color="muted" className="mt-2">
              View all database operations
            </Text>
          </div>
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            Loading audit data...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4 md:px-6 lg:px-8">

        <div className="mb-8 flex justify-between items-center">
          <div>
            <Heading variant="h1">Audit Log</Heading>
            <Text variant="body" color="muted" className="mt-2">
              Database operations and audit trail
            </Text>
          </div>
          <Button
            onClick={() => fetchAuditData(currentPage)}
            className="bg-black text-white hover:opacity-90"
          >
            Refresh
          </Button>
        </div>

      <div className="space-y-4">
        <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-4">
          <Heading variant="h3">All Database Operations</Heading>
          <Text variant="bodySmall" color="muted" className="mt-1">
            {auditData?.total_count || 0} operations found
          </Text>
        </div>

        {/* Mobile Card View */}
        <div className="md:hidden space-y-3">
          {(auditData?.audit_logs || []).length > 0 ? (
            (auditData?.audit_logs || []).map((entry) => (
              <div key={entry.id} className="bg-card border rounded-lg shadow-sm p-4">
                {/* Header: Timestamp and Action Badge */}
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-3 pb-3 border-b border-border">
                  <div>
                    <Text variant="caption" color="muted">{formatTimestamp(entry.timestamp)}</Text>
                    <div className="mt-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full whitespace-nowrap ${
                        entry.action === 'PLAYER_MERGE'
                          ? 'bg-primary/10 text-primary'
                          : entry.action === 'PLAYER_MERGE_UNDO'
                          ? 'bg-success/10 text-success'
                          : entry.action.includes('VERIFY')
                          ? 'bg-info/10 text-info'
                          : entry.action.includes('UPDATE')
                          ? 'bg-warning/10 text-warning'
                          : entry.action.includes('INSERT')
                          ? 'bg-success/10 text-success'
                          : entry.action.includes('DELETE')
                          ? 'bg-destructive/10 text-destructive'
                          : entry.action.includes('IMPORT')
                          ? 'bg-primary/10 text-primary'
                          : 'bg-muted text-muted-foreground'
                      }`}>
                        {entry.action.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actor */}
                <div className="mb-3">
                  <Text variant="caption" color="muted" className="uppercase">Actor</Text>
                  <Text variant="bodySmall" className="mt-1">{entry.actor_id}</Text>
                </div>

                {/* Details */}
                <div className="mb-4">
                  <Text variant="caption" color="muted" className="uppercase">Details</Text>
                  <Text variant="bodySmall" className="mt-1">
                    {entry.description || 'No description available'}
                  </Text>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-3 border-t border-border">
                  <Button
                    onClick={() => handleViewDetails(entry.id)}
                    variant="outline"
                    className="flex-1 min-h-[44px]"
                  >
                    View Details
                  </Button>
                  {entry.can_undo && (
                    <Button
                      onClick={() => handleUndoClick(entry)}
                      variant="outline"
                      className="flex-1 min-h-[44px] text-destructive hover:text-destructive border-destructive/50"
                    >
                      Undo
                    </Button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
              <Text variant="body" color="muted">No audit entries found</Text>
            </div>
          )}
        </div>

        {/* Desktop Table View */}
        <div className="hidden md:block">
          <EnhancedDataTable
            data={auditData?.audit_logs || []}
            columns={auditColumns}
            emptyState={
              <div className="text-center text-muted-foreground">
                No audit entries found
              </div>
            }
            className="rounded-lg"
            variant="default"
          />
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
          <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border p-6 w-full max-w-4xl my-8">
            <div>
              <h3 className="text-2xl font-semibold tracking-tight mb-6">Operation Details</h3>
              <div key="operation-details" className="space-y-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><strong>Operation ID:</strong> {selectedOperation.operation_id}</div>
                  <div><strong>Action:</strong> {selectedOperation.action}</div>
                  <div><strong>Timestamp:</strong> {formatTimestamp(selectedOperation.timestamp)}</div>
                  <div><strong>Actor:</strong> {selectedOperation.actor}</div>
                </div>
                {selectedOperation.before_state ? (
                  <div>
                    {selectedOperation.action === 'PLAYER_MERGE' ? (
                      <div>
                        <Text variant="body" weight="medium" as="h4" className="mb-4">Before State</Text>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                          {renderPlayerInfo((selectedOperation.before_state as Record<string, unknown>).target_player, "Target Player")}
                          <div>
                            <Text variant="body" weight="medium" as="h5" className="mb-2 text-gray-900">Source Players</Text>
                            {Array.isArray((selectedOperation.before_state as Record<string, unknown>).source_players) ? (
                              ((selectedOperation.before_state as Record<string, unknown>).source_players as unknown[]).map((player: unknown, idx: number) => (
                                <div key={idx} className="mb-3">
                                  {renderPlayerInfo(player, `Source Player ${idx + 1}`)}
                                </div>
                              ))
                            ) : null}
                          </div>
                        </div>
                      </div>
                    ) : (
                      renderGenericData(selectedOperation.before_state, "Before State")
                    )}
                  </div>
                ) : null}
                {selectedOperation.after_state ? (
                  <div>
                    {selectedOperation.action === 'PLAYER_MERGE' ? (
                      <div>
                        <Text variant="body" weight="medium" as="h4" className="mb-4">After State</Text>
                        {renderPlayerInfo((selectedOperation.after_state as Record<string, unknown>).target_player, "Merged Player")}
                      </div>
                    ) : (
                      renderGenericData(selectedOperation.after_state, "After State")
                    )}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <Button
                onClick={handleCancel}
                variant="outline"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Undo Confirmation Modal */}
      {showUndoConfirm && selectedOperation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border p-6 w-full max-w-md">
            <Heading variant="h3" className="mb-4">
              Confirm Undo Operation
            </Heading>
            
            <Text variant="bodySmall" color="muted" className="mb-4">
              This will undo the merge operation and restore all players to their original state.
              This action cannot be undone.
            </Text>

            <div className="bg-sophisticated-gold-extralight border border-sophisticated-gold rounded p-3 mb-4">
              <div className="text-sm text-sophisticated-gold-deep">
                <strong>Operation:</strong> {selectedOperation.action}<br/>
                <strong>Date:</strong> {formatTimestamp(selectedOperation.timestamp)}<br/>
                <strong>Players affected:</strong> {
                  (() => {
                    const beforeState = selectedOperation.before_state as Record<string, unknown> | undefined;
                    const sourcePlayers = beforeState && Array.isArray(beforeState.source_players) ? beforeState.source_players : [];
                    return sourcePlayers.length + 1;
                  })()
                }
              </div>
            </div>

            {(showAdminInput && !hasAdminSession) && (
              <div className="mb-4">
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  Admin Code *
                </Text>
                <input
                  type="password"
                  value={manualAdminCode}
                  onChange={(e) => setManualAdminCode(e.target.value)}
                  placeholder="Enter admin code..."
                  className="w-full px-3 py-2 border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring bg-background text-foreground"
                />
              </div>
            )}
            
            {hasAdminSession && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="text-sm text-success">
                  <strong>Using stored admin session</strong><br/>
                  Game: {publicCode}<br/>
                  Admin code is automatically applied for this session.
                </div>
              </div>
            )}

            <div className="flex justify-end gap-3">
              <Button
                onClick={handleCancel}
                disabled={undoLoading}
                variant="outline"
              >
                Cancel
              </Button>
              <Button
                onClick={executeUndo}
                disabled={undoLoading}
                variant="destructive"
                className="bg-red-600 hover:bg-red-700"
              >
                {undoLoading ? 'Undoing...' : 'Confirm Undo'}
              </Button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}