import { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '../shared/ui/button';
import { Heading, Text, Code } from '../shared/ui/typography';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="max-w-md w-full mx-auto text-center">
            <div className="mb-4">
              <Heading variant="h1" className="mb-2">Oops!</Heading>
              <Heading variant="h4" color="muted" className="mb-4">Something went wrong</Heading>
            </div>

            <div className="bg-card rounded-lg shadow-md p-6 mb-6 border border-border">
              <Text variant="body" className="mb-4">
                We apologize for the inconvenience. An unexpected error has occurred.
              </Text>

              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className="text-left mb-4">
                  <summary className="cursor-pointer mb-2">
                    <Text variant="bodySmall" color="muted">Error Details (Development)</Text>
                  </summary>
                  <Code variant="block">
                    {this.state.error.stack}
                  </Code>
                </details>
              )}
            </div>

            <div className="space-y-3">
              <Button
                onClick={() => window.location.reload()}
                className="w-full"
              >
                <Text variant="bodySmall" weight="medium">Reload Page</Text>
              </Button>

              <Button
                onClick={() => window.history.back()}
                variant="secondary"
                className="w-full"
              >
                <Text variant="bodySmall" weight="medium">Go Back</Text>
              </Button>

              <a
                href="/"
                className="block w-full bg-success text-success-foreground px-4 py-2 rounded hover:bg-success/90 transition-colors text-center"
              >
                <Text variant="bodySmall" weight="medium">Return Home</Text>
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}