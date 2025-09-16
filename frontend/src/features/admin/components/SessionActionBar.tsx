import { Upload, Loader2, CheckCircle2 } from "lucide-react";

interface GameActionBarProps {
  onCancel: () => void;
  onUpload: () => void;
  balanced: boolean;
  isLoading: boolean;
  isSuccess?: boolean;
}

const GameActionBar: React.FC<GameActionBarProps> = ({
  onCancel,
  onUpload,
  balanced,
  isLoading,
  isSuccess,
}) => (
  <div className="mt-6 space-y-4">
    <div className="flex items-center justify-between">
      <button
        className="bg-gray-200 px-4 py-2 rounded hover:bg-gray-300 transition-colors"
        onClick={onCancel}
        disabled={isLoading}
      >
        Cancel
      </button>
      <button
        className={`px-6 py-2 rounded text-white flex items-center gap-2 transition-colors ${
          isSuccess
            ? "bg-green-600"
            : balanced && !isLoading
            ? "bg-green-600 hover:bg-green-700"
            : "bg-gray-400 cursor-not-allowed"
        }`}
        onClick={onUpload}
        disabled={(!balanced || isLoading) && !isSuccess}
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" /> Uploading...
          </>
        ) : isSuccess ? (
          <>
            <CheckCircle2 className="h-4 w-4" /> Upload Successful
          </>
        ) : (
          <>
            <Upload className="h-4 w-4" /> Upload to Database
          </>
        )}
      </button>
    </div>
    
    {/* Inline success message */}
    {isSuccess && (
      <div className="bg-green-50 border-l-4 border-green-400 rounded p-3 text-right">
        <p className="text-green-800 text-sm font-medium">
          ✓ Session uploaded successfully! The data has been saved to your database.
        </p>
      </div>
    )}
  </div>
);
export default GameActionBar;
