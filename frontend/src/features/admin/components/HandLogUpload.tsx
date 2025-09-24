import { AlertCircle, CheckCircle, Upload, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { Button } from '../../../shared/ui/button';
import { Text } from '../../../shared/ui/typography';

interface HandLogUploadProps {
  onFileSelect: (file: File) => void;
  uploadStatus: 'idle' | 'uploading' | 'success' | 'needs_mapping' | 'error';
  uploadResult?: {
    events_created?: number;
    hands_created?: number;
    total_hands?: number;
  };
  error?: string;
  onClearFile?: () => void;
}

export default function HandLogUpload({
  onFileSelect,
  uploadStatus,
  uploadResult,
  error,
  onClearFile
}: HandLogUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      onFileSelect(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);

    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) {
      setSelectedFile(file);
      onFileSelect(file);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (onClearFile) {
      onClearFile();
    }
  };

  return (
    <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <Text variant="body" weight="semibold">Hand Log CSV (Optional)</Text>
          <Text variant="caption" color="muted" className="mt-1">
            Upload PokerNow hand history for detailed analytics. Will be processed when you click "Upload to Database"
          </Text>
        </div>
      </div>

      {uploadStatus === 'success' ? (
        <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
            <div className="flex-1">
              <Text variant="bodySmall" weight="semibold" className="text-green-900 dark:text-green-100">
                Hand Log Uploaded Successfully
              </Text>
              {uploadResult && (
                <Text variant="caption" color="muted" className="mt-1">
                  {uploadResult.events_created} events from {uploadResult.hands_created} hands imported
                </Text>
              )}
            </div>
            <Button
              onClick={handleClear}
              variant="ghost"
              size="icon-sm"
              className="text-green-600 hover:text-green-800"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : uploadStatus === 'error' ? (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
            <div className="flex-1">
              <Text variant="bodySmall" weight="semibold" className="text-red-900 dark:text-red-100">
                Upload Failed
              </Text>
              <Text variant="caption" color="muted" className="mt-1">
                {error || 'An error occurred during upload'}
              </Text>
            </div>
            <Button
              onClick={handleClear}
              variant="ghost"
              size="icon-sm"
              className="text-red-600 hover:text-red-800"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : selectedFile ? (
        <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Upload className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <div>
                <Text variant="bodySmall" weight="medium" className="text-blue-900 dark:text-blue-100">
                  {selectedFile.name}
                </Text>
                <Text variant="caption" color="muted">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </Text>
              </div>
            </div>
            <Button
              onClick={handleClear}
              variant="ghost"
              size="icon-sm"
              className="text-blue-600 hover:text-blue-800"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`
            border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
            ${isDragActive
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50 hover:bg-accent/50'
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
          />
          <Upload className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
          {isDragActive ? (
            <Text variant="bodySmall" color="muted">Drop the CSV file here...</Text>
          ) : (
            <>
              <Text variant="bodySmall" weight="medium">
                Drag & drop hand log CSV here
              </Text>
              <Text variant="caption" color="muted" className="mt-1">
                or click to browse files
              </Text>
            </>
          )}
        </div>
      )}

      {uploadStatus === 'uploading' && (
        <div className="mt-3 flex items-center gap-2">
          <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
          <Text variant="caption" color="muted">Processing hand log...</Text>
        </div>
      )}
    </div>
  );
}