import { type ReactNode } from 'react';
import { useAdminSession } from '../contexts/AdminSessionContext';
import { Heading, Text } from '../shared/ui/typography';

interface ProtectedRouteProps {
  children: ReactNode;
  requireAdmin?: boolean;
}

export default function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { hasAdminSession } = useAdminSession();

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