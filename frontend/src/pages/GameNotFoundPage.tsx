import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../shared/ui/button';
import { Heading, Text } from '../shared/ui/typography';

export const GameNotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background z-50">
      <div className="max-w-md w-full mx-auto text-center px-4">
        <div className="mb-8">
          <div className="text-6xl mb-4">🃏</div>
          <Heading variant="h1" className="mb-4">Game Not Found</Heading>
          <Text variant="bodyLarge" color="muted" className="mb-2">
            This game code doesn't exist or may have been deleted.
          </Text>
          <Text variant="body" color="muted">
            Please check the code and try again.
          </Text>
        </div>

        <div className="space-y-4">
          <Button
            size="lg"
            onClick={() => window.history.back()}
            className="w-full"
          >
            Take Me Back
          </Button>

          <Button
            onClick={() => navigate('/')}
            variant="outline"
            className="w-full"
          >
            Return Home
          </Button>
        </div>
      </div>
    </div>
  );
};
