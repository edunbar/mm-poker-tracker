import { useAuth } from '@clerk/clerk-react';
import { useEffect, type ReactNode } from 'react';
import { setClerkTokenGetter } from '../api/client';

interface ClerkAuthWrapperProps {
  children: ReactNode;
}

/**
 * ClerkAuthWrapper
 *
 * This component bridges Clerk authentication with our API client.
 * It provides the Clerk token getter function to the axios interceptor,
 * ensuring all API calls include a valid Clerk session token.
 */
export function ClerkAuthWrapper({ children }: ClerkAuthWrapperProps) {
  const { getToken, isLoaded } = useAuth();

  useEffect(() => {
    if (isLoaded) {
      // Inject Clerk's getToken function into the API client
      setClerkTokenGetter(async () => {
        try {
          return await getToken();
        } catch (error) {
          // eslint-disable-next-line no-console
          console.error('Failed to get Clerk token:', error);
          return null;
        }
      });
    }
  }, [getToken, isLoaded]);

  return <>{children}</>;
}
