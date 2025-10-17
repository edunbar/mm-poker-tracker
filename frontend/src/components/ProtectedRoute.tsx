import { type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAdminSession } from '../contexts/AdminSessionContext';
import { useClerkAuth } from '../hooks/useClerkAuth';
import { Heading, Text } from '../shared/ui/typography';

interface ProtectedRouteProps {
  children: ReactNode;
  requireAdmin?: boolean;
  requireAuth?: boolean;
}

// Helper function to extract public code from URL pathname
function extractPublicCodeFromPath(pathname: string): string | null {
  const pathParts = pathname.split('/').filter(part => part.length > 0);

  // For routes like /ingest/ABC123, /summary/ABC123, /admin/ABC123, etc.
  if (pathParts.length >= 2) {
    const potentialCode = pathParts[1];
    // Check if it looks like a public code (5 chars, alphanumeric)
    if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }

  // For routes like /ABC123 (direct game access)
  if (pathParts.length === 1) {
    const potentialCode = pathParts[0];
    if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }

  return null;
}

export default function ProtectedRoute({
  children,
  requireAdmin = false,
  requireAuth = false,
}: ProtectedRouteProps) {
  const location = useLocation();
  const { isSignedIn, isLoaded } = useClerkAuth();
  const { hasAdminSession: hasAdminSessionForGame } = useAdminSession();

  // Extract public code from URL to check admin session
  const publicCode = extractPublicCodeFromPath(location.pathname);
  const hasAdminSession = publicCode ? hasAdminSessionForGame(publicCode) : false;

  // Handle user authentication requirement
  if (requireAuth) {
    if (!isLoaded) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto" />
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        </div>
      );
    }

    if (!isSignedIn) {
      return <Navigate to="/sign-in" state={{ from: location.pathname }} replace />;
    }
  }

  // Handle admin authentication requirement
  if (requireAdmin && !hasAdminSession) {
    return (
      <div className="flex flex-col items-center justify-center min-h-64 text-center">
        <div className="mb-6">
          <svg className="mx-auto h-12 w-12 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0 0v3m0-3h3m-3 0h-3m-3-9a3 3 0 106 0v1M9 12a3 3 0 006 0v-1M9 12H6m3 0h6" />
          </svg>
        </div>
        <Heading variant="h3" className="mb-2">Access Denied</Heading>
        <Text variant="body" color="muted" className="mb-4">
          You don't have permission to view this page. An admin session is required.
        </Text>
        <Text variant="bodySmall" color="muted">
          Please log in with admin credentials to access this content.
        </Text>
      </div>
    );
  }

  return <>{children}</>;
}