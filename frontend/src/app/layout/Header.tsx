import { Bug, Shield, X } from 'lucide-react';
import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { submitBugReport, type BugReportData } from '../../api/bugReport';
import BugReportModal from '../../components/BugReportModal';
import { useAdminSession } from '../../contexts/AdminSessionContext';
import { useToast } from '../../contexts/ToastContext';
import { Button } from '../../shared/ui/button';
import { Input } from '../../shared/ui/input';
import { Text } from '../../shared/ui/typography';

// Helper function to extract public code from URL pathname
function extractPublicCodeFromPath(pathname: string): string | null {
  const pathParts = pathname.split('/').filter(part => part.length > 0);

  // Skip if we're on the landing page
  if (pathParts.length === 0) {
    return null;
  }

  // For routes like /ingest/ABC123, /summary/ABC123, /payments/ABC123, etc.
  if (pathParts.length >= 2) {
    const potentialCode = pathParts[1];
    // Check if it looks like a public code (5 chars, alphanumeric)
    if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }

  // For routes like /ABC123 (direct game access)
  if (pathParts.length === 1) {
    // Check if it looks like a public code (5 chars, alphanumeric)
    const potentialCode = pathParts[0];
    if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }

  return null;
}

export function Header() {
  const { hasAdminSession, setAdminSession, publicCode: contextPublicCode } = useAdminSession();
  const { showSuccess, showError } = useToast();
  const location = useLocation();
  const [isBugReportModalOpen, setIsBugReportModalOpen] = useState(false);
  const [showAdminLogin, setShowAdminLogin] = useState(false);
  const [adminCode, setAdminCode] = useState('');

  // Get public code from URL first (prioritize current page), then fall back to admin session context
  const urlPublicCode = extractPublicCodeFromPath(location.pathname);
  const currentPublicCode = urlPublicCode || contextPublicCode;

  const handleAdminLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (adminCode && currentPublicCode) {
      setAdminSession(adminCode, currentPublicCode);
      setAdminCode('');
      setShowAdminLogin(false);
    }
  };

  const handleBugReportSubmit = async (data: BugReportData) => {
    try {
      await submitBugReport(data);
      showSuccess('Success', 'Bug report submitted successfully! Thank you for your feedback.');
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to submit bug report:', error);
      showError('Error', 'Failed to submit bug report. Please try again later.');
      throw error; // Re-throw to prevent modal from closing
    }
  };

  return (
    <>
      <header className="border-b border-border bg-card">
        <div className="w-full px-4 py-3 font-medium flex items-center justify-between text-card-foreground">
          <Text variant="bodyLarge" weight="semibold">HomeGame</Text>

          <div className="flex items-center gap-2">
            {/* Admin Login Button - Only show when not logged in as admin and in game context */}
            {!hasAdminSession && currentPublicCode && (
              <button
                onClick={() => setShowAdminLogin(true)}
                className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
                title="Admin login"
              >
                <Shield className="h-4 w-4" />
                <Text variant="bodySmall" as="span" className="hidden sm:inline">Admin Login</Text>
              </button>
            )}

            {/* Bug Report Button */}
            <button
              onClick={() => setIsBugReportModalOpen(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
              title="Report a bug"
            >
              <Bug className="h-4 w-4" />
              <Text variant="bodySmall" as="span" className="hidden sm:inline">Report Bug</Text>
            </button>
          </div>
        </div>
      </header>

      {/* Bug Report Modal */}
      <BugReportModal
        isOpen={isBugReportModalOpen}
        onClose={() => setIsBugReportModalOpen(false)}
        onSubmit={handleBugReportSubmit}
      />

      {/* Admin Login Modal */}
      {showAdminLogin && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-md w-full mx-4">
            <div className="flex items-center justify-between p-6 border-b border-border">
              <Text variant="bodyLarge" weight="semibold">Admin Login</Text>
              <Button
                onClick={() => {
                  setShowAdminLogin(false);
                  setAdminCode('');
                }}
                variant="ghost"
                size="icon-sm"
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-6 h-6" />
              </Button>
            </div>

            <form onSubmit={handleAdminLogin} className="p-6 space-y-4">
              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  Admin Code
                </Text>
                <Input
                  type="password"
                  value={adminCode}
                  onChange={(e) => setAdminCode(e.target.value)}
                  placeholder="Enter admin code"
                  autoFocus
                />
              </div>

              <div className="flex justify-end space-x-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowAdminLogin(false);
                    setAdminCode('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!adminCode}
                >
                  Login
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}