import { useAdminSession } from '../contexts/AdminSessionContext';
import { useNavigate, useLocation } from 'react-router-dom';

interface AdminSessionStatusProps {
  className?: string;
  compact?: boolean;
}

export default function AdminSessionStatus({ className = '', compact = false }: AdminSessionStatusProps) {
  const { publicCode, hasAdminSession, clearAdminSession } = useAdminSession();
  const navigate = useNavigate();
  const location = useLocation();

  const handleClearSession = () => {
    const currentPublicCode = publicCode;
    clearAdminSession();
    
    // Check if user is on an admin page and redirect to game summary
    const adminPaths = ['/ingest/', '/ledger/', '/players/', '/audit/'];
    const isOnAdminPage = adminPaths.some(path => location.pathname.includes(path));
    
    if (isOnAdminPage && currentPublicCode) {
      navigate(`/summary/${currentPublicCode}`);
    }
  };

  if (!hasAdminSession) {
    return null;
  }

  return (
    <div className={`bg-green-50 border border-green-200 rounded-lg p-3 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="text-sm text-green-800">
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
        <button
          onClick={handleClearSession}
          className="ml-4 text-xs bg-green-200 text-green-800 px-2 py-1 rounded hover:bg-green-300"
          title="Clear admin session"
        >
          Clear Session
        </button>
      </div>
    </div>
  );
}