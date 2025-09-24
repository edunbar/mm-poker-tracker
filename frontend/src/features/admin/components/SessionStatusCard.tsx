import { CheckCircle2, AlertTriangle } from "lucide-react";

interface GameStatusCardProps {
  status: "success" | "error" | null;
  balanced: boolean;
  errorMessage?: string | null;
  ledgerCsvStatus?: {
    success: boolean;
    size_bytes?: number;
    error?: string;
    url?: string;
    content?: string;
  } | null;
  onViewCsv?: () => void;
}

const GameStatusCard: React.FC<GameStatusCardProps> = ({
  status,
  balanced,
  errorMessage,
  ledgerCsvStatus,
  onViewCsv,
}) => {
  if (status === "success") {
    return (
      <div className="mb-6 p-4 bg-success/10 border-l-4 border-success rounded">
        <div className="flex items-center">
          <CheckCircle2 className="h-5 w-5 text-success mr-3" />
          <div>
            <div className="text-success font-medium">Success!</div>
            <div className="text-success/80">Game has been saved to the database successfully.</div>
          </div>
        </div>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="mb-6 p-4 bg-destructive/10 border-l-4 border-destructive rounded">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 text-destructive mr-3" />
          <div>
            <div className="text-destructive font-medium">Error</div>
            <div className="text-destructive/80">{errorMessage || "Please fix invalid cells and ensure totals are balanced before uploading."}</div>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-4 mb-6">
      <div className="flex items-center">
        {balanced ? (
          <CheckCircle2 className="h-5 w-5 text-success mr-3" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-destructive mr-3" />
        )}
        <div className="flex-1">
          <div
            className={`font-medium ${
              balanced ? "text-success" : "text-destructive"
            }`}
          >
            {balanced ? "Ready to upload" : "Needs attention"}
          </div>
          <div className={`text-sm ${
            balanced ? "text-success/80" : "text-destructive/80"
          }`}>
            {balanced
              ? "Totals are balanced. You can safely upload this game."
              : "Enter numeric values for Buy In and Cash Out. Net and totals will auto‑recalculate."}
          </div>
        </div>
      </div>

      {ledgerCsvStatus && (
        <div className={`mt-3 pt-3 border-t border-border flex items-center gap-3 ${
          ledgerCsvStatus.success
            ? 'text-success'
            : 'text-destructive'
        }`}>
          {ledgerCsvStatus.success ? (
            <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
          ) : (
            <AlertTriangle className="h-5 w-5 flex-shrink-0" />
          )}
          <div className="flex-1">
            <div
              className={`font-medium ${
                ledgerCsvStatus.success ? "text-success" : "text-destructive"
              }`}
            >
              Ledger CSV {ledgerCsvStatus.success ? 'Retrieved' : 'Failed'}
            </div>
            <div className={`text-sm ${
              ledgerCsvStatus.success ? "text-success/80" : "text-destructive/80"
            }`}>
              {ledgerCsvStatus.success ? (
                <>
                  Successfully fetched ledger data ({ledgerCsvStatus.size_bytes} bytes) -{' '}
                  <button
                    onClick={onViewCsv}
                    className="underline hover:opacity-80"
                  >
                    View CSV
                  </button>
                </>
              ) : (
                `Could not retrieve ledger CSV: ${ledgerCsvStatus.error || 'Unknown error'}`
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GameStatusCard;
