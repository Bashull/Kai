import React, { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center h-full gap-4 text-center p-8">
          <div className="text-4xl">⚠️</div>
          <h2 className="text-xl font-semibold text-red-400">Panel caído</h2>
          <p className="text-sm text-gray-400 max-w-sm">
            {this.state.error?.message ?? 'Error inesperado en este panel.'}
          </p>
          <button
            onClick={this.handleReset}
            className="px-4 py-2 bg-kai-primary text-white rounded-lg text-sm hover:opacity-80 transition-opacity"
          >
            Reintentar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
