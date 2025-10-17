import { renderHook, act } from '@testing-library/react';
import { AdminSessionProvider, useAdminSession } from './AdminSessionContext';
import type { ReactNode } from 'react';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('AdminSessionContext - Multi-game support', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <AdminSessionProvider>{children}</AdminSessionProvider>
  );

  it('stores admin codes for multiple games separately', () => {
    const { result } = renderHook(() => useAdminSession(), { wrapper });

    // Set admin codes for two different games
    act(() => {
      result.current.setAdminSession('admin-code-1', 'GAME1');
    });

    act(() => {
      result.current.setAdminSession('admin-code-2', 'GAME2');
    });

    // Verify both admin codes are stored correctly
    expect(result.current.getAdminCode('GAME1')).toBe('admin-code-1');
    expect(result.current.getAdminCode('GAME2')).toBe('admin-code-2');
    expect(result.current.hasAdminSession('GAME1')).toBe(true);
    expect(result.current.hasAdminSession('GAME2')).toBe(true);
  });

  it('returns null for games without admin sessions', () => {
    const { result } = renderHook(() => useAdminSession(), { wrapper });

    act(() => {
      result.current.setAdminSession('admin-code-1', 'GAME1');
    });

    expect(result.current.getAdminCode('GAME1')).toBe('admin-code-1');
    expect(result.current.getAdminCode('GAME2')).toBeNull();
    expect(result.current.hasAdminSession('GAME1')).toBe(true);
    expect(result.current.hasAdminSession('GAME2')).toBe(false);
  });

  it('clears specific game admin session', () => {
    const { result } = renderHook(() => useAdminSession(), { wrapper });

    act(() => {
      result.current.setAdminSession('admin-code-1', 'GAME1');
      result.current.setAdminSession('admin-code-2', 'GAME2');
    });

    // Clear only GAME1
    act(() => {
      result.current.clearAdminSession('GAME1');
    });

    expect(result.current.getAdminCode('GAME1')).toBeNull();
    expect(result.current.getAdminCode('GAME2')).toBe('admin-code-2');
    expect(result.current.hasAdminSession('GAME1')).toBe(false);
    expect(result.current.hasAdminSession('GAME2')).toBe(true);
  });

  it('clears all game admin sessions', () => {
    const { result } = renderHook(() => useAdminSession(), { wrapper });

    act(() => {
      result.current.setAdminSession('admin-code-1', 'GAME1');
      result.current.setAdminSession('admin-code-2', 'GAME2');
    });

    // Clear all sessions
    act(() => {
      result.current.clearAdminSession();
    });

    expect(result.current.getAdminCode('GAME1')).toBeNull();
    expect(result.current.getAdminCode('GAME2')).toBeNull();
    expect(result.current.hasAdminSession('GAME1')).toBe(false);
    expect(result.current.hasAdminSession('GAME2')).toBe(false);
  });

  it('persists admin codes to localStorage', () => {
    const { result } = renderHook(() => useAdminSession(), { wrapper });

    act(() => {
      result.current.setAdminSession('admin-code-1', 'GAME1');
    });

    act(() => {
      result.current.setAdminSession('admin-code-2', 'GAME2');
    });

    // Verify localStorage has the correct data
    const stored = JSON.parse(
      localStorageMock.getItem('admin_sessions') || '{}'
    );
    expect(stored).toEqual({
      GAME1: 'admin-code-1',
      GAME2: 'admin-code-2',
    });
  });

  it('loads admin codes from localStorage on mount', () => {
    // Pre-populate localStorage
    localStorageMock.setItem(
      'admin_sessions',
      JSON.stringify({
        GAME1: 'admin-code-1',
        GAME2: 'admin-code-2',
      })
    );

    const { result } = renderHook(() => useAdminSession(), { wrapper });

    expect(result.current.getAdminCode('GAME1')).toBe('admin-code-1');
    expect(result.current.getAdminCode('GAME2')).toBe('admin-code-2');
  });

  it('migrates old single-session format to new multi-session format', () => {
    // Pre-populate localStorage with old format
    localStorageMock.setItem(
      'admin_sessions',
      JSON.stringify({
        adminCode: 'old-admin-code',
        publicCode: 'OLDGAME',
      })
    );

    const { result } = renderHook(() => useAdminSession(), { wrapper });

    // Verify migration happened
    expect(result.current.getAdminCode('OLDGAME')).toBe('old-admin-code');

    // Verify localStorage was updated to new format
    const stored = JSON.parse(
      localStorageMock.getItem('admin_sessions') || '{}'
    );
    expect(stored).toEqual({
      OLDGAME: 'old-admin-code',
    });
  });

  it('returns all public codes with admin sessions', () => {
    const { result } = renderHook(() => useAdminSession(), { wrapper });

    act(() => {
      result.current.setAdminSession('admin-code-1', 'GAME1');
    });

    act(() => {
      result.current.setAdminSession('admin-code-2', 'GAME2');
    });

    act(() => {
      result.current.setAdminSession('admin-code-3', 'GAME3');
    });

    const allSessions = result.current.getAllAdminSessions();
    expect(allSessions).toHaveLength(3);
    expect(allSessions).toContain('GAME1');
    expect(allSessions).toContain('GAME2');
    expect(allSessions).toContain('GAME3');
  });

  it('updates admin code for existing game', () => {
    const { result } = renderHook(() => useAdminSession(), { wrapper });

    act(() => {
      result.current.setAdminSession('old-admin-code', 'GAME1');
    });

    expect(result.current.getAdminCode('GAME1')).toBe('old-admin-code');

    // Update with new admin code
    act(() => {
      result.current.setAdminSession('new-admin-code', 'GAME1');
    });

    expect(result.current.getAdminCode('GAME1')).toBe('new-admin-code');
  });
});
