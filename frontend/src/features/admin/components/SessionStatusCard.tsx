import { CheckCircle2, AlertTriangle } from "lucide-react";

interface GameStatusCardProps {
  status: "success" | "error" | null;
  balanced: boolean;
  errorMessage?: string | null;
}

const GameStatusCard: React.FC<GameStatusCardProps> = ({
  status,
  balanced,
  errorMessage,
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
        <div>
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
    </div>
  );
};

export default GameStatusCard;
