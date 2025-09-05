import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useToast } from '../../../contexts/ToastContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';

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
  const { adminCode: sessionAdminCode, hasAdminSession } = useAdminSession();
  const { showSuccess, showError } = useToast();
  const { title } = useGameTitle(publicCode || '');
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
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/players/verification`);
      setData(response.data);
    } catch (error) {
      console.error('Error fetching verification data:', error);
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
        `http://localhost:8000/api/games/${publicCode}/players/find-duplicates`,
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
      console.error('Error checking for duplicates:', error);
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
        `http://localhost:8000/api/games/${publicCode}/players/merge`,
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
      console.error('Error merging players:', error);
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
        url: `http://localhost:8000/api/games/${publicCode}/players/${editingPlayer.player_id}/${endpoint}`,
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
      console.error('Error saving player:', error);
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
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-6xl mx-auto px-4">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Player Verification</h1>
            <p className="mt-2 text-gray-600">
              Game <span className="font-mono bg-gray-100 px-2 py-1 rounded">{title}</span>
            </p>
          </div>
          <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
            Loading verification data...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Player Verification</h1>
          <p className="mt-2 text-gray-600">
            Manage and verify player identities for game <span className="font-mono bg-gray-100 px-2 py-1 rounded">{title}</span>
          </p>
        </div>
      
      <div className="space-y-6">
        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('unverified')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'unverified'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Unverified Players ({data?.unverified_count || 0})
            </button>
            <button
              onClick={() => setActiveTab('verified')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'verified'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Verified Players ({data?.verified_count || 0})
            </button>
          </nav>
        </div>

        
        {/* Table */}
        <div className="bg-white rounded-lg border shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {activeTab === 'unverified' ? 'Display Name' : 'Verified Name'}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  External ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Sessions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-gray-500">
                    Loading players...
                  </td>
                </tr>
              ) : currentPlayers.map((player) => (
                <tr key={player.player_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {player.display_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {player.external_id || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {player.session_count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => handleEdit(player, activeTab === 'verified')}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>

        {!loading && currentPlayers.length === 0 && (
          <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
            <p className="text-gray-500">
              No {activeTab} players found.
            </p>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && editingPlayer && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl my-8">
            <h3 className="text-lg font-medium text-gray-900 mb-6">
              {editingPlayer.is_verified ? 'Edit Verified Player' : 'Verify Player'}
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Display Name (read-only)
                </label>
                <input
                  type="text"
                  value={editingPlayer.display_name}
                  readOnly
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  External ID (read-only)
                </label>
                <input
                  type="text"
                  value={editingPlayer.external_id || '-'}
                  readOnly
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  All Names Used (read-only)
                </label>
                <input
                  type="text"
                  value={editingPlayer.all_names.join(', ')}
                  readOnly
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Verified Name *
                </label>
                <input
                  type="text"
                  value={verifiedName}
                  onChange={(e) => handleVerifiedNameChange(e.target.value)}
                  placeholder="Enter real player name..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-sm text-gray-500 mt-1">
                  This will be used to identify the player across sessions
                </p>
              </div>
              
              {/* Duplicate Detection Section */}
              {duplicateDetection && duplicateDetection.match_count > 0 && (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-center mb-3">
                    <div className="text-yellow-600 mr-2">⚠️</div>
                    <h4 className="font-medium text-yellow-800">
                      Found {duplicateDetection.match_count} potential match{duplicateDetection.match_count > 1 ? 'es' : ''} for '{duplicateDetection.verified_name}'
                    </h4>
                  </div>
                  <p className="text-sm text-yellow-700 mb-3">
                    Do you want to merge these players? This will combine all their session data.
                  </p>
                  
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {duplicateDetection.potential_matches.map((match) => (
                      <label key={match.player_id} className="flex items-start p-3 bg-white rounded border hover:bg-gray-50 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedMergeTargets.includes(match.player_id)}
                          onChange={(e) => handleMergeToggle(match.player_id, e.target.checked)}
                          className="mt-1 mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <div className="font-medium text-gray-900">
                              {match.display_name} 
                              {match.is_verified && <span className="ml-2 px-2 py-1 text-xs bg-green-100 text-green-800 rounded">Verified</span>}
                            </div>
                            <div className="text-sm text-gray-500">{match.session_count} sessions</div>
                          </div>
                          {match.external_id && (
                            <div className="text-sm text-gray-600">ID: {match.external_id}</div>
                          )}
                          <div className="text-xs text-gray-500 mt-1">
                            Used names: {match.session_names.slice(0, 3).join(', ')}
                            {match.session_names.length > 3 && ` (+${match.session_names.length - 3} more)`}
                          </div>
                          <div className="text-xs text-blue-600 mt-1">
                            {match.match_reasons.join(', ')}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                  
                  {selectedMergeTargets.length > 0 && (
                    <div className="mt-3 p-3 bg-blue-50 rounded border">
                      <div className="text-sm text-blue-800">
                        <strong>Merge Preview:</strong> {selectedMergeTargets.length} player{selectedMergeTargets.length > 1 ? 's' : ''} will be merged into this verification.
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  External ID {editingPlayer.is_verified ? '' : '*'}
                </label>
                <input
                  type="text"
                  value={externalId}
                  onChange={(e) => setExternalId(e.target.value)}
                  placeholder="Enter PokerNow player ID..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-sm text-gray-500 mt-1">
                  {editingPlayer.is_verified ? 'Update the player\'s PokerNow ID' : 'Required to verify player - this is their PokerNow ID'}
                </p>
              </div>

              {showAdminInput && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Admin Code *
                  </label>
                  <input
                    type="password"
                    value={manualAdminCode}
                    onChange={(e) => setManualAdminCode(e.target.value)}
                    placeholder="Enter admin code..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              )}
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={handleCancel}
                disabled={modalLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={modalLoading || !verifiedName.trim() || (!editingPlayer.is_verified && !externalId.trim())}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {modalLoading ? (
                  selectedMergeTargets.length > 0 ? 'Merging...' : 'Saving...'
                ) : (
                  selectedMergeTargets.length > 0 ? `Merge & Verify (${selectedMergeTargets.length + 1} players)` : 'Save'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Confirmation Modal */}
      {showMergeConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-60">
          <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Confirm Player Merge
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              This will merge {selectedMergeTargets.length} player{selectedMergeTargets.length > 1 ? 's' : ''} into one. All session data will be combined. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowMergeConfirmation(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={executeMerge}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg hover:bg-red-700"
              >
                Confirm Merge
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}