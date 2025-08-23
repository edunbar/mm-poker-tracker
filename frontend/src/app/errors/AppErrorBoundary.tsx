import React from "react";

type State = { hasError: boolean; error?: unknown };

export default class AppErrorBoundary extends React.Component<
  React.PropsWithChildren<{}>,
  State
> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: unknown) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <h1 className="text-xl font-semibold">Something went wrong</h1>
          <p className="text-sm text-gray-600">Please refresh and try again.</p>
        </div>
      );
    }
    return this.props.children;
  }
}
