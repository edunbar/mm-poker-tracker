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
      <div className="mb-6 p-4 bg-green-50 border-l-4 border-green-400 rounded">
        <div className="flex items-center">
          <CheckCircle2 className="h-5 w-5 text-green-600 mr-3" />
          <div>
            <div className="text-green-800 font-medium">Success!</div>
            <div className="text-green-700">Game has been saved to the database successfully.</div>
          </div>
        </div>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400 rounded">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 text-red-600 mr-3" />
          <div>
            <div className="text-red-800 font-medium">Error</div>
            <div className="text-red-700">{errorMessage || "Please fix invalid cells and ensure totals are balanced before uploading."}</div>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="bg-white rounded-lg border shadow-sm p-4 mb-6">
      <div className="flex items-center">
        {balanced ? (
          <CheckCircle2 className="h-5 w-5 text-green-600 mr-3" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-red-600 mr-3" />
        )}
        <div>
          <div
            className={`font-medium ${
              balanced ? "text-green-800" : "text-red-800"
            }`}
          >
            {balanced ? "Ready to upload" : "Needs attention"}
          </div>
          <div className={`text-sm ${
            balanced ? "text-green-700" : "text-red-700"
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
