import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface AdminSessionContextType {
  getAdminCode: (publicCode: string) => string | null;
  setAdminSession: (adminCode: string, publicCode: string) => void;
  clearAdminSession: (publicCode?: string) => void;
  hasAdminSession: (publicCode: string) => boolean;
  getAllAdminSessions: () => string[];
}

const AdminSessionContext = createContext<AdminSessionContextType | undefined>(undefined);

const ADMIN_SESSION_KEY = 'admin_sessions';

interface AdminSessionProviderProps {
  children: ReactNode;
}

export function AdminSessionProvider({ children }: AdminSessionProviderProps) {
  // Store admin codes as a map: { [publicCode]: adminCode }
  const [adminCodes, setAdminCodes] = useState<Record<string, string>>({});

  // Load sessions from localStorage on mount
  useEffect(() => {
    const savedSessions = localStorage.getItem(ADMIN_SESSION_KEY);
    if (savedSessions) {
      try {
        const parsed = JSON.parse(savedSessions);
        // Check if it's the new format (object) or old format (single session)
        if (typeof parsed === 'object' && parsed !== null) {
          if ('adminCode' in parsed && 'publicCode' in parsed) {
            // Old format - migrate to new format
            const { adminCode, publicCode } = parsed;
            const newFormat = { [publicCode]: adminCode };
            setAdminCodes(newFormat);
            localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify(newFormat));
          } else {
            // New format - use directly
            setAdminCodes(parsed);
          }
        }
      } catch {
        localStorage.removeItem(ADMIN_SESSION_KEY);
      }
    }
  }, []);

  const getAdminCode = (publicCode: string): string | null => {
    return adminCodes[publicCode] || null;
  };

  const setAdminSession = (adminCode: string, publicCode: string) => {
    const newAdminCodes = {
      ...adminCodes,
      [publicCode]: adminCode
    };
    setAdminCodes(newAdminCodes);

    // Save to localStorage
    localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify(newAdminCodes));
  };

  const clearAdminSession = (publicCode?: string) => {
    if (publicCode) {
      // Clear specific game
      const newAdminCodes = { ...adminCodes };
      delete newAdminCodes[publicCode];
      setAdminCodes(newAdminCodes);
      localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify(newAdminCodes));
    } else {
      // Clear all games
      setAdminCodes({});
      localStorage.removeItem(ADMIN_SESSION_KEY);
    }
  };

  const hasAdminSession = (publicCode: string): boolean => {
    return Boolean(adminCodes[publicCode]);
  };

  const getAllAdminSessions = (): string[] => {
    return Object.keys(adminCodes);
  };

  const value: AdminSessionContextType = {
    getAdminCode,
    setAdminSession,
    clearAdminSession,
    hasAdminSession,
    getAllAdminSessions
  };

  return (
    <AdminSessionContext.Provider value={value}>
      {children}
    </AdminSessionContext.Provider>
  );
}

export function useAdminSession() {
  const context = useContext(AdminSessionContext);
  if (context === undefined) {
    throw new Error('useAdminSession must be used within an AdminSessionProvider');
  }
  return context;
}