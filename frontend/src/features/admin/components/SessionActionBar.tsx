import React from "react";
import { Upload, Loader2 } from "lucide-react";

interface GameActionBarProps {
  onCancel: () => void;
  onUpload: () => void;
  balanced: boolean;
  isLoading: boolean;
}

const GameActionBar: React.FC<GameActionBarProps> = ({
  onCancel,
  onUpload,
  balanced,
  isLoading,
}) => (
  <div className="mt-6 flex items-center justify-between">
    <button
      className="bg-gray-200 px-4 py-2 rounded"
      onClick={onCancel}
      disabled={isLoading}
    >
      Cancel
    </button>
    <button
      className={`px-4 py-2 rounded text-white flex items-center gap-2 ${
        balanced && !isLoading
          ? "bg-green-600 hover:bg-green-700"
          : "bg-gray-400 cursor-not-allowed"
      }`}
      onClick={onUpload}
      disabled={!balanced || isLoading}
    >
      {isLoading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" /> Uploading
        </>
      ) : (
        <>
          <Upload className="h-4 w-4" /> Upload to Database
        </>
      )}
    </button>
  </div>
);
export default GameActionBar;
