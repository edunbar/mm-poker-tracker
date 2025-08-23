import React from "react";
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
      <div className="border-emerald-200 bg-emerald-50 rounded-lg p-4 flex gap-3 items-center">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
        <div>
          <div className="font-semibold text-emerald-700">
            Upload successful
          </div>
          <div className="text-sm">
            Game has been saved to the database and synced to your sheet.
          </div>
        </div>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="border-red-200 bg-red-50 rounded-lg p-4 flex gap-3 items-center">
        <AlertTriangle className="h-5 w-5 text-red-600" />
        <div>
          <div className="font-semibold text-red-700">Upload blocked</div>
          <div className="text-sm">
            Please fix invalid cells and ensure totals are balanced before
            uploading.
          </div>
          {errorMessage && (
            <div className="text-sm text-red-600 mt-2">{errorMessage}</div>
          )}
        </div>
      </div>
    );
  }
  return (
    <div className="bg-white rounded-lg p-4 flex gap-3 items-center">
      {balanced ? (
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
      ) : (
        <AlertTriangle className="h-5 w-5 text-red-600" />
      )}
      <div>
        <div
          className={`font-semibold ${
            balanced ? "text-emerald-700" : "text-red-700"
          }`}
        >
          {balanced ? "Ready to upload" : "Needs attention"}
        </div>
        <div className="text-sm">
          {balanced
            ? "Totals are balanced. You can safely upload this game."
            : "Enter numeric values for Buy In and Cash Out. Net and totals will auto‑recalculate."}
        </div>
      </div>
    </div>
  );
};

export default GameStatusCard;
