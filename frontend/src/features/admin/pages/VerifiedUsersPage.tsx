import axios from 'axios';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { API_BASE_URL } from '../../../config/api';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useToast } from '../../../contexts/ToastContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';
import { Button } from '../../../shared/ui/button';
import { Heading, Text } from '../../../shared/ui/typography';

interface UnverifiedPlayer {
  player_id: string;
  display_name: string;
  external_id: string | null;
  session_count: number;
  all_names: string[];
}

interface VerifiedPlayer {
  player_id: string;
  display_name: string;
  external_id: string | null;
  session_count: number;
  all_names: string[];
}

interface VerificationData {
  unverified_players: UnverifiedPlayer[];
  verified_players: VerifiedPlayer[];
  unverified_count: number;
  verified_count: number;
}

interface EditingPlayer {
  player_id: string;
  display_name: string;
  external_id: string | null;
  all_names: string[];
  is_verified: boolean;
}

interface PotentialMatch {
  player_id: string;
  display_name: string;
  external_id: string | null;
  session_count: number;
  session_names: string[];
  is_verified: boolean;
  match_score: number;
  match_reasons: string[];
}

interface DuplicateDetection {
  verified_name: string;
  potential_matches: PotentialMatch[];
  match_count: number;
}

export default function VerifiedUsersPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const { adminCode: sessionAdminCode, hasAdminSession: _hasAdminSession } = useAdminSession();
  const { showSuccess: _showSuccess, showError } = useToast();
  const { title: _title } = useGameTitle(publicCode || '');
  const [data, setData] = useState<VerificationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'unverified' | 'verified'>('unverified');
  const [showModal, setShowModal] = useState(false);
  const [editingPlayer, setEditingPlayer] = useState<EditingPlayer | null>(null);
  const [verifiedName, setVerifiedName] = useState('');
  const [externalId, setExternalId] = useState('');
  const [manualAdminCode, setManualAdminCode] = useState('');
  const [showAdminInput, setShowAdminInput] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [duplicateDetection, setDuplicateDetection] = useState<DuplicateDetection | null>(null);
  const [selectedMergeTargets, setSelectedMergeTargets] = useState<string[]>([]);
  const [showMergeConfirmation, setShowMergeConfirmation] = useState(false);
  
  // Use session admin code if available, otherwise manual input
  const effectiveAdminCode = sessionAdminCode || manualAdminCode;

  useEffect(() => {
    if (publicCode) {
      fetchVerificationData();
    }
  }, [publicCode]);

  const fetchVerificationData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/players/verification`);
      setData(response.data);
    } catch (error) {
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async (player: UnverifiedPlayer | VerifiedPlayer, isVerified: boolean) => {
    setEditingPlayer({
      player_id: player.player_id,
      display_name: player.display_name,
      external_id: player.external_id,
      all_names: player.all_names,
      is_verified: isVerified
    });
    setVerifiedName(isVerified ? player.display_name : '');
    setExternalId(player.external_id || '');
    setShowModal(true);
  };

  const checkForDuplicates = async (name: string) => {
    if (!name.trim() || name.length < 2) {
      setDuplicateDetection(null);
      return;
    }

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/games/${publicCode}/players/find-duplicates`,
        {
          verified_name: name.trim(),
          exclude_player_id: editingPlayer?.player_id
        }
      );
      
      const detection = response.data;
      if (detection.match_count > 0) {
        setDuplicateDetection(detection);
      } else {
        setDuplicateDetection(null);
      }
    } catch (error) {
      setDuplicateDetection(null);
    }
  };

  const handleVerifiedNameChange = (value: string) => {
    setVerifiedName(value);
    // Debounce the duplicate check
    const timeoutId = setTimeout(() => checkForDuplicates(value), 500);
    return () => clearTimeout(timeoutId);
  };

  const handleMergeToggle = (playerId: string, checked: boolean) => {
    if (checked) {
      setSelectedMergeTargets(prev => [...prev, playerId]);
    } else {
      setSelectedMergeTargets(prev => prev.filter(id => id !== playerId));
    }
  };

  const executeMerge = async () => {
    if (!editingPlayer || selectedMergeTargets.length === 0) return;
    
    if (!effectiveAdminCode.trim()) {
      setShowAdminInput(true);
      return;
    }

    try {
      setModalLoading(true);
      
      await axios.post(
        `${API_BASE_URL}/api/games/${publicCode}/players/merge`,
        {
          target_player_id: editingPlayer.player_id,
          source_player_ids: selectedMergeTargets,
          verified_name: verifiedName.trim(),
          external_id: externalId.trim() || null
        },
        { headers: { 'X-Admin-Code': effectiveAdminCode } }
      );

      setShowModal(false);
      setShowMergeConfirmation(false);
      setShowAdminInput(false);
      setEditingPlayer(null);
      setVerifiedName('');
      setExternalId('');
      setManualAdminCode('');
      setDuplicateDetection(null);
      setSelectedMergeTargets([]);
      fetchVerificationData();
    } catch (error) {
      showError('Merge Failed', 'Failed to merge players. Please check your admin code.');
    } finally {
      setModalLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editingPlayer || !verifiedName.trim()) return;
    
    // If there are selected merge targets, execute merge instead
    if (selectedMergeTargets.length > 0) {
      executeMerge();
      return;
    }
    
    if (!effectiveAdminCode.trim()) {
      setShowAdminInput(true);
      return;
    }

    try {
      setModalLoading(true);
      const endpoint = editingPlayer.is_verified ? 'verify' : 'verify';
      const method = editingPlayer.is_verified ? 'put' : 'post';
      
      await axios({
        method,
        url: `${API_BASE_URL}/api/games/${publicCode}/players/${editingPlayer.player_id}/${endpoint}`,
        data: { 
          verified_name: verifiedName.trim(),
          external_id: externalId.trim() || null
        },
        headers: { 'X-Admin-Code': effectiveAdminCode }
      });

      setShowModal(false);
      setShowAdminInput(false);
      setEditingPlayer(null);
      setVerifiedName('');
      setExternalId('');
      setManualAdminCode('');
      setDuplicateDetection(null);
      setSelectedMergeTargets([]);
      fetchVerificationData();
    } catch (error) {
      showError('Save Failed', 'Failed to save player. Please check your admin code.');
    } finally {
      setModalLoading(false);
    }
  };

  const handleCancel = () => {
    setShowModal(false);
    setShowAdminInput(false);
    setEditingPlayer(null);
    setVerifiedName('');
    setExternalId('');
    setManualAdminCode('');
    setDuplicateDetection(null);
    setSelectedMergeTargets([]);
    setShowMergeConfirmation(false);
  };

  const currentPlayers = activeTab === 'unverified' ? data?.unverified_players || [] : data?.verified_players || [];

  if (loading) {
    return (
      <div className="min-h-screen bg-background py-8">
        <div className="max-w-6xl mx-auto px-4">
          <div className="mb-8">
            <Heading variant="h1">Player Verification</Heading>
            <Text variant="body" color="muted" className="mt-2">
              Manage and verify player identities
            </Text>
          </div>
          <div className="card-stripe p-12 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
            <Text variant="body" color="muted">Loading verification data...</Text>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-8">
          <Heading variant="h1">Player Verification</Heading>
          <Text variant="body" color="muted" className="mt-2">
            Manage and verify player identities
          </Text>
        </div>
      
      <div className="space-y-6">
        {/* Tabs */}
        <div className="border-b border-border">
          <nav className="-mb-px flex space-x-8">
            <Button
              onClick={() => setActiveTab('unverified')}
              variant="ghost"
              className={`py-4 px-1 border-b-2 transition-colors rounded-none ${
                activeTab === 'unverified'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
              }`}
            >
              <Text variant="bodySmall" weight="medium">
                Unverified Players ({data?.unverified_count || 0})
              </Text>
            </Button>
            <Button
              onClick={() => setActiveTab('verified')}
              variant="ghost"
              className={`py-4 px-1 border-b-2 transition-colors rounded-none ${
                activeTab === 'verified'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
              }`}
            >
              <Text variant="bodySmall" weight="medium">
                Verified Players ({data?.verified_count || 0})
              </Text>
            </Button>
          </nav>
        </div>

        
        {/* Table */}
        <div className="overflow-auto rounded-xl border border-border bg-card">
            <table className="min-w-full">
            <thead className="bg-card border-b border-border">
              <tr className="border-b border-border">
                <Text variant="caption" weight="medium" color="muted" as="th" className="px-6 py-3 text-left uppercase tracking-wider">
                  {activeTab === 'unverified' ? 'Display Name' : 'Verified Name'}
                </Text>
                <Text variant="caption" weight="medium" color="muted" as="th" className="px-6 py-3 text-left uppercase tracking-wider">
                  External ID
                </Text>
                <Text variant="caption" weight="medium" color="muted" as="th" className="px-6 py-3 text-left uppercase tracking-wider">
                  Sessions
                </Text>
                <Text variant="caption" weight="medium" color="muted" as="th" className="px-6 py-3 text-left uppercase tracking-wider">
                  Actions
                </Text>
              </tr>
            </thead>
            <tbody className="bg-card">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center">
                    <Text color="muted">Loading players...</Text>
                  </td>
                </tr>
              ) : currentPlayers.map((player) => (
                <tr key={player.player_id} className="border-b border-border hover:bg-accent/50">
                  <td className="px-6 py-4">
                    <Text weight="medium">{player.display_name}</Text>
                  </td>
                  <td className="px-6 py-4">
                    <Text>{player.external_id || '-'}</Text>
                  </td>
                  <td className="px-6 py-4">
                    <Text>{player.session_count}</Text>
                  </td>
                  <td className="px-6 py-4">
                    <Button
                      onClick={() => handleEdit(player, activeTab === 'verified')}
                      variant="secondary"
                      size="sm"
                    >
                      Edit
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!loading && currentPlayers.length === 0 && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            <Text variant="body" color="muted">
              No {activeTab} players found.
            </Text>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && editingPlayer && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-card text-card-foreground rounded-lg shadow-xl p-6 w-full max-w-2xl my-8 border border-border">
            <Heading variant="h3" className="mb-6">
              {editingPlayer.is_verified ? 'Edit Verified Player' : 'Verify Player'}
            </Heading>
            
            <div className="space-y-4">
              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  Display Name (read-only)
                </Text>
                <input
                  type="text"
                  value={editingPlayer.display_name}
                  readOnly
                  className="w-full px-3 py-2 border border-input rounded-lg bg-muted text-muted-foreground"
                />
              </div>
              
              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  External ID (read-only)
                </Text>
                <input
                  type="text"
                  value={editingPlayer.external_id || '-'}
                  readOnly
                  className="w-full px-3 py-2 border border-input rounded-lg bg-muted text-muted-foreground"
                />
              </div>
              
              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  All Names Used (read-only)
                </Text>
                <input
                  type="text"
                  value={editingPlayer.all_names.join(', ')}
                  readOnly
                  className="w-full px-3 py-2 border border-input rounded-lg bg-muted text-muted-foreground"
                />
              </div>
              
              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  Verified Name *
                </Text>
                <input
                  type="text"
                  value={verifiedName}
                  onChange={(e) => handleVerifiedNameChange(e.target.value)}
                  placeholder="Enter real player name..."
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring placeholder:text-muted-foreground"
                />
                <Text variant="bodySmall" color="muted" className="mt-1">
                  This will be used to identify the player across sessions
                </Text>
              </div>
              
              {/* Duplicate Detection Section */}
              {duplicateDetection && duplicateDetection.match_count > 0 && (
                <div className="p-4 bg-warning/10 border border-warning rounded-lg">
                  <div className="flex items-center mb-3">
                    <div className="text-warning mr-2">⚠️</div>
                    <Text variant="body" weight="medium" color="warning" as="h4">
                      Found {duplicateDetection.match_count} potential match{duplicateDetection.match_count > 1 ? 'es' : ''} for '{duplicateDetection.verified_name}'
                    </Text>
                  </div>
                  <Text variant="bodySmall" color="warning" className="mb-3">
                    Do you want to merge these players? This will combine all their session data.
                  </Text>
                  
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {duplicateDetection.potential_matches.map((match) => (
                      <label key={match.player_id} className="flex items-start p-3 bg-card rounded border border-border hover:bg-accent/50 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedMergeTargets.includes(match.player_id)}
                          onChange={(e) => handleMergeToggle(match.player_id, e.target.checked)}
                          className="mt-1 mr-3 h-4 w-4 text-primary focus:ring-ring border-input rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <div>
                              <Text weight="medium">
                                {match.display_name}
                                {match.is_verified && <span className="ml-2 px-2 py-1 text-xs bg-success/20 text-success rounded">Verified</span>}
                              </Text>
                            </div>
                            <Text variant="bodySmall" color="muted">{match.session_count} sessions</Text>
                          </div>
                          {match.external_id && (
                            <Text variant="bodySmall" color="muted">ID: {match.external_id}</Text>
                          )}
                          <Text variant="caption" color="muted" className="mt-1">
                            Used names: {match.session_names.slice(0, 3).join(', ')}
                            {match.session_names.length > 3 && ` (+${match.session_names.length - 3} more)`}
                          </Text>
                          <Text variant="caption" color="primary" className="mt-1">
                            {match.match_reasons.join(', ')}
                          </Text>
                        </div>
                      </label>
                    ))}
                  </div>
                  
                  {selectedMergeTargets.length > 0 && (
                    <div className="mt-3 p-3 bg-primary/10 rounded border border-primary/20">
                      <Text variant="bodySmall" color="primary">
                        <strong>Merge Preview:</strong> {selectedMergeTargets.length} player{selectedMergeTargets.length > 1 ? 's' : ''} will be merged into this verification.
                      </Text>
                    </div>
                  )}
                </div>
              )}
              
              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  External ID {editingPlayer.is_verified ? '' : '*'}
                </Text>
                <input
                  type="text"
                  value={externalId}
                  onChange={(e) => setExternalId(e.target.value)}
                  placeholder="Enter PokerNow player ID..."
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring placeholder:text-muted-foreground"
                />
                <Text variant="bodySmall" color="muted" className="mt-1">
                  {editingPlayer.is_verified ? 'Update the player\'s PokerNow ID' : 'Required to verify player - this is their PokerNow ID'}
                </Text>
              </div>

              {showAdminInput && (
                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                    Admin Code *
                  </Text>
                  <input
                    type="password"
                    value={manualAdminCode}
                    onChange={(e) => setManualAdminCode(e.target.value)}
                    placeholder="Enter admin code..."
                    className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring placeholder:text-muted-foreground"
                  />
                </div>
              )}
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <Button
                onClick={handleCancel}
                disabled={modalLoading}
                variant="outline"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={modalLoading || !verifiedName.trim() || (!editingPlayer.is_verified && !externalId.trim())}
              >
                {modalLoading ? (
                  selectedMergeTargets.length > 0 ? 'Merging...' : 'Saving...'
                ) : (
                  selectedMergeTargets.length > 0 ? `Merge & Verify (${selectedMergeTargets.length + 1} players)` : 'Save'
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Confirmation Modal */}
      {showMergeConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-60">
          <div className="bg-card text-card-foreground rounded-lg shadow-xl p-6 w-96 max-w-md mx-4 border border-border">
            <Heading variant="h3" className="mb-4">
              Confirm Player Merge
            </Heading>
            <Text variant="bodySmall" color="muted" className="mb-4">
              This will merge {selectedMergeTargets.length} player{selectedMergeTargets.length > 1 ? 's' : ''} into one. All session data will be combined. This action cannot be undone.
            </Text>
            <div className="flex justify-end gap-3">
              <Button
                onClick={() => setShowMergeConfirmation(false)}
                variant="outline"
              >
                Cancel
              </Button>
              <Button
                onClick={executeMerge}
                variant="destructive"
              >
                Confirm Merge
              </Button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}