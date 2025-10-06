import { useNavigate, useLocation } from 'react-router-dom';
import { useAdminSession } from '../contexts/AdminSessionContext';
import { Button } from '../shared/ui/button';

interface AdminSessionStatusProps {
  className?: string;
  compact?: boolean;
  publicCode?: string;
}

// Helper function to extract public code from URL pathname
function extractPublicCodeFromPath(pathname: string): string | null {
  const pathParts = pathname.split('/').filter(part => part.length > 0);

  if (pathParts.length >= 2) {
    const potentialCode = pathParts[1];
    if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }

  if (pathParts.length === 1) {
    const potentialCode = pathParts[0];
    if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }

  return null;
}

export default function AdminSessionStatus({ className = '', compact = false, publicCode: propPublicCode }: AdminSessionStatusProps) {
  const { hasAdminSession: hasAdminSessionForGame, clearAdminSession } = useAdminSession();
  const navigate = useNavigate();
  const location = useLocation();

  // Use prop if provided, otherwise extract from URL
  const publicCode = propPublicCode || extractPublicCodeFromPath(location.pathname);
  const hasAdminSession = publicCode ? hasAdminSessionForGame(publicCode) : false;

  const handleClearSession = () => {
    if (publicCode) {
      clearAdminSession(publicCode);

      // Check if user is on an admin page and redirect to game summary
      const adminPaths = ['/ingest/', '/ledger/', '/players/', '/audit/'];
      const isOnAdminPage = adminPaths.some(path => location.pathname.includes(path));

      if (isOnAdminPage) {
        navigate(`/summary/${publicCode}`);
      }
    }
  };

  if (!hasAdminSession) {
    return null;
  }

  return (
    <div className={`bg-success/10 border border-success rounded-lg p-3 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="text-sm text-success">
          <div className="flex items-center">
            <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <strong>Admin Session Active</strong>
          </div>
          {!compact && (
            <div className="mt-1">
              Game: <span className="font-mono">{publicCode}</span><br/>
              Admin code automatically applied to all operations
            </div>
          )}
        </div>
        <Button
          onClick={handleClearSession}
          variant="ghost"
          size="sm"
          className="ml-4 text-xs bg-success/20 text-success px-2 py-1 hover:bg-success/30"
          title="Clear admin session"
        >
          Clear Session
        </Button>
      </div>
    </div>
  );
}