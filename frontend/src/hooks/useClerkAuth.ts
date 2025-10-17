import { useUser } from '@clerk/clerk-react';

/**
 * useClerkAuth
 *
 * Custom hook that provides a consistent interface for Clerk authentication.
 * This hook serves as a drop-in replacement for the old useAuth() hook,
 * minimizing changes needed in existing components.
 *
 * @returns {Object} Authentication state
 * @returns {Object|null} user - The current user object from Clerk
 * @returns {boolean} isSignedIn - Whether the user is signed in
 * @returns {boolean} isLoaded - Whether Clerk has finished loading
 */
export function useClerkAuth() {
  const { user, isSignedIn, isLoaded } = useUser();

  return {
    user,
    isSignedIn: !!isSignedIn,
    isLoaded: !!isLoaded,
    // Legacy compatibility
    isAuthenticated: !!isSignedIn,
    isLoading: !isLoaded,
  };
}
