import { useMutation } from 'react-query';
import { API_BASE_URL } from '../../../config/api';
import { useAdminSession } from '../../../contexts/AdminSessionContext';

interface UploadHandLogParams {
  publicCode: string;
  sessionId: string;
  file: File;
  playerMappings?: Record<string, string>;
}

interface UploadHandLogResponse {
  status: 'success' | 'needs_mapping';
  events_created?: number;
  hands_created?: number;
  total_hands?: number;
  total_events?: number;
  unmatched_players?: Array<{
    display_name: string;
    external_id: string | null;
  }>;
}

export function useUploadHandLog() {
  const { adminCode } = useAdminSession();

  return useMutation<UploadHandLogResponse, Error, UploadHandLogParams>({
    mutationFn: async ({ publicCode, sessionId, file, playerMappings }) => {
      const formData = new FormData();
      formData.append('file', file);

      if (playerMappings) {
        formData.append('player_mappings', JSON.stringify(playerMappings));
      }

      const response = await fetch(
        `${API_BASE_URL}/api/games/${publicCode}/sessions/${sessionId}/upload-hand-log`,
        {
          method: 'POST',
          headers: {
            'X-Admin-Code': adminCode || '',
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to upload hand log');
      }

      return response.json();
    },
  });
}