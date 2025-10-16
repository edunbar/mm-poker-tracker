import { Check, Copy } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../shared/ui/button';
import { Heading, Text } from '../shared/ui/typography';

interface LiveGameCreatedModalProps {
  joinCode: string;
  liveGameId: string;
  publicCode: string;
  onClose: () => void;
}

export function LiveGameCreatedModal({ joinCode, publicCode, onClose }: LiveGameCreatedModalProps) {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);

  const joinUrl = `${window.location.origin}/join-live/${joinCode}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(joinUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
    }
  };

  const handleGoToAdmin = () => {
    navigate(`/live/${publicCode}/${joinCode}/admin`);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-md w-full">
        <div className="p-6 space-y-6">
          {/* Success Header */}
          <div className="text-center">
            <div className="text-6xl mb-4">🎉</div>
            <Heading variant="h3">Live Game Created!</Heading>
            <Text variant="body" color="muted" className="mt-2">
              Share the code below with your players
            </Text>
          </div>

          {/* Join Code Display */}
          <div className="bg-primary/10 border border-primary/30 rounded-lg p-6 text-center">
            <Text variant="caption" color="muted" className="mb-2">
              JOIN CODE
            </Text>
            <Heading variant="h1" className="text-primary font-mono tracking-wider">
              {joinCode}
            </Heading>
          </div>

          {/* Join URL */}
          <div className="space-y-2">
            <Text variant="bodySmall" color="muted">
              Or share this link:
            </Text>
            <div className="flex gap-2">
              <div className="flex-1 bg-muted rounded-lg p-3 overflow-x-auto">
                <Text variant="bodySmall" className="font-mono break-all">
                  {joinUrl}
                </Text>
              </div>
              <Button
                variant="outline"
                size="icon-sm"
                onClick={handleCopy}
                className="flex-shrink-0"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-success" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            {copied && (
              <Text variant="caption" className="text-success">
                Copied to clipboard!
              </Text>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Button variant="outline" onClick={onClose} className="flex-1">
              Done
            </Button>
            <Button onClick={handleGoToAdmin} className="flex-1">
              Go to Admin Panel
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
