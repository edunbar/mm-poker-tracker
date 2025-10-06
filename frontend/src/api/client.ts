import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Auto-attach Authorization and X-Admin-Code headers
apiClient.interceptors.request.use(
  (config) => {
    // Attach auth token if exists
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Attach X-Admin-Code for live game endpoints if admin session exists
    // Extract joinCode from URL pattern: /api/live-games/:joinCode/*
    const liveGameMatch = config.url?.match(/\/api\/live-games\/([A-Z0-9]{4})\//);
    if (liveGameMatch && liveGameMatch[1]) {
      const joinCode = liveGameMatch[1];

      // Try to get publicCode from localStorage-cached live game data
      // This works because useLiveGameInfo() fetches and caches the live game data
      try {
        const adminSessionsStr = localStorage.getItem('admin_sessions');
        if (adminSessionsStr) {
          const adminSessions: Record<string, string> = JSON.parse(adminSessionsStr);

          // We need to find the publicCode for this joinCode
          // Check if we have it stored in a separate mapping
          const joinCodeMappingStr = localStorage.getItem('join_code_to_public_code');
          if (joinCodeMappingStr) {
            const joinCodeMapping: Record<string, string> = JSON.parse(joinCodeMappingStr);
            const publicCode = joinCodeMapping[joinCode];

            if (publicCode && adminSessions[publicCode]) {
              config.headers['X-Admin-Code'] = adminSessions[publicCode];
            }
          }
        }
      } catch (error) {
        // Silently fail - admin code is optional
        console.debug('Failed to attach X-Admin-Code header:', error);
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: Handle errors and suppress expected ones
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';

    // Suppress expected errors (don't log to console)
    // These are normal application states, not actual errors
    const isExpectedError =
      (status === 404 && url.includes('/live-games/active')) || // No active game exists
      (status === 410 && url.includes('/api/live-games/'));     // Game has been closed

    // Only handle auth errors and unexpected errors
    if (!isExpectedError) {
      if (status === 401) {
        const hadToken = localStorage.getItem('auth_token');

        // Only clear token if we had one (expired scenario)
        if (hadToken) {
          localStorage.removeItem('auth_token');

          // Don't redirect if already on auth pages
          const currentPath = window.location.pathname;
          if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
            window.location.href = '/login';
          }
        }
      }
    }

    return Promise.reject(error);
  }
);
