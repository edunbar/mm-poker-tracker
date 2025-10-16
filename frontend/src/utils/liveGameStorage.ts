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
      return;
    }

    const data: ActiveLiveGame = { joinCode, publicCode };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));

    // Dispatch custom event to notify components
    window.dispatchEvent(new CustomEvent('activeLiveGameChanged', { detail: data }));
  } catch (error) {
    // Silently handle storage errors
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
      return null;
    }

    const parsed = JSON.parse(data);
    // Validate structure
    if (parsed && typeof parsed.joinCode === 'string' && typeof parsed.publicCode === 'string') {
      return parsed as ActiveLiveGame;
    }

    return null;
  } catch (error) {
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

    // Dispatch custom event to notify components
    window.dispatchEvent(new CustomEvent('activeLiveGameChanged', { detail: null }));
  } catch (error) {
    // Silently handle storage errors
  }
}
