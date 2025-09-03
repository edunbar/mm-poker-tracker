import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AdminSessionContextType {
  adminCode: string | null;
  publicCode: string | null;
  setAdminSession: (adminCode: string, publicCode: string) => void;
  clearAdminSession: () => void;
  hasAdminSession: boolean;
}

const AdminSessionContext = createContext<AdminSessionContextType | undefined>(undefined);

const ADMIN_SESSION_KEY = 'admin_session';

interface AdminSessionProviderProps {
  children: ReactNode;
}

export function AdminSessionProvider({ children }: AdminSessionProviderProps) {
  const [adminCode, setAdminCode] = useState<string | null>(null);
  const [publicCode, setPublicCode] = useState<string | null>(null);

  // Load session from localStorage on mount
  useEffect(() => {
    const savedSession = localStorage.getItem(ADMIN_SESSION_KEY);
    if (savedSession) {
      try {
        const { adminCode: savedAdminCode, publicCode: savedPublicCode } = JSON.parse(savedSession);
        if (savedAdminCode && savedPublicCode) {
          setAdminCode(savedAdminCode);
          setPublicCode(savedPublicCode);
        }
      } catch (error) {
        console.error('Failed to parse admin session:', error);
        localStorage.removeItem(ADMIN_SESSION_KEY);
      }
    }
  }, []);

  const setAdminSession = (newAdminCode: string, newPublicCode: string) => {
    setAdminCode(newAdminCode);
    setPublicCode(newPublicCode);
    
    // Save to localStorage
    localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify({
      adminCode: newAdminCode,
      publicCode: newPublicCode
    }));
  };

  const clearAdminSession = () => {
    setAdminCode(null);
    setPublicCode(null);
    localStorage.removeItem(ADMIN_SESSION_KEY);
  };

  const hasAdminSession = Boolean(adminCode && publicCode);

  const value: AdminSessionContextType = {
    adminCode,
    publicCode,
    setAdminSession,
    clearAdminSession,
    hasAdminSession
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