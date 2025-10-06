/**
 * Local Storage utilities for tracking active live game participation
 *
 * Stores information about the user's currently active live game session
 * to enable navigation between pages while maintaining live game context.
 */

const STORAGE_KEY = 'active_live_game';

export interface ActiveLiveGame {
  joinCode: string;
  publicCode: string;
}

/**
 * Store the user's active live game information
 */
export function setActiveLiveGame(joinCode: string, publicCode: string): void {
  try {
    if (!publicCode || publicCode.trim() === '') {
      console.warn('[LiveGameStorage] Attempted to store invalid publicCode:', publicCode);
      return;
    }

    const data: ActiveLiveGame = { joinCode, publicCode };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    console.log('[LiveGameStorage] Stored active live game:', data);

    // Dispatch custom event to notify components
    window.dispatchEvent(new CustomEvent('activeLiveGameChanged', { detail: data }));
  } catch (error) {
    console.error('Failed to store active live game:', error);
  }
}

/**
 * Retrieve the user's active live game information
 * Returns null if no active game or if parsing fails
 */
export function getActiveLiveGame(): ActiveLiveGame | null {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) {
      console.log('[LiveGameStorage] No active live game found');
      return null;
    }

    const parsed = JSON.parse(data);
    // Validate structure
    if (parsed && typeof parsed.joinCode === 'string' && typeof parsed.publicCode === 'string') {
      console.log('[LiveGameStorage] Retrieved active live game:', parsed);
      return parsed as ActiveLiveGame;
    }

    console.warn('[LiveGameStorage] Invalid active live game data:', parsed);
    return null;
  } catch (error) {
    console.error('Failed to retrieve active live game:', error);
    return null;
  }
}

/**
 * Clear the user's active live game information
 * Called when user leaves or when game closes
 */
export function clearActiveLiveGame(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
    console.log('[LiveGameStorage] Cleared active live game');

    // Dispatch custom event to notify components
    window.dispatchEvent(new CustomEvent('activeLiveGameChanged', { detail: null }));
  } catch (error) {
    console.error('Failed to clear active live game:', error);
  }
}
