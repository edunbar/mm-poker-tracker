import { useState } from 'react';
import { Bug } from 'lucide-react';
import { submitBugReport, type BugReportData } from '../../api/bugReport';
import BugReportModal from '../../components/BugReportModal';
import { useAdminSession } from '../../contexts/AdminSessionContext';
import { useToast } from '../../contexts/ToastContext';
import { Text } from '../../shared/ui/typography';

export function Header() {
  const { hasAdminSession: _hasAdminSession, publicCode: _publicCode, clearAdminSession: _clearAdminSession } = useAdminSession();
  const { showSuccess, showError } = useToast();
  const [isBugReportModalOpen, setIsBugReportModalOpen] = useState(false);

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
      </header>

      {/* Bug Report Modal */}
      <BugReportModal
        isOpen={isBugReportModalOpen}
        onClose={() => setIsBugReportModalOpen(false)}
        onSubmit={handleBugReportSubmit}
      />
    </>
  );
}