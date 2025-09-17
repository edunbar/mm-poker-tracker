import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../shared/ui/button';
import { Heading, Text } from '../shared/ui/typography';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="max-w-md w-full mx-auto text-center">
        <div className="mb-8">
          <Heading variant="h1" className="text-6xl mb-4">404</Heading>
          <Heading variant="h2" className="mb-2">Page Not Found</Heading>
          <Text variant="body" color="muted">
            The page you're looking for doesn't exist or has been moved.
          </Text>
        </div>

        <div className="space-y-4">
          <Button
            size="lg"
            onClick={() => navigate('/')}
          >
<Text variant="body" weight="medium">Return Home</Text>
          </Button>

          <div className="pt-4">
            <Button
              onClick={() => window.history.back()}
              variant="link"
            >
<Text variant="body">Go Back</Text>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};