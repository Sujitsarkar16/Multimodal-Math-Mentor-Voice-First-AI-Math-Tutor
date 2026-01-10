import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import { WorkspaceProvider } from './context/WorkspaceContext';

// Error boundary component to catch rendering errors
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Application error:', error, errorInfo);
  }

  handleReset = () => {
    // Clear all session storage to reset the app state
    sessionStorage.clear();
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-8">
          <div className="max-w-md w-full bg-neutral-900 border border-red-500/30 rounded-xl p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
              <Icon icon="lucide:alert-triangle" className="text-red-400" width={32} />
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">Something went wrong</h2>
            <p className="text-neutral-400 text-sm mb-6">
              The application encountered an error. Click the button below to reset and try again.
            </p>
            <button
              onClick={this.handleReset}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-colors"
            >
              Reset Application
            </button>
            {this.state.error && (
              <div className="mt-6 p-4 bg-neutral-950 rounded-lg text-left">
                <p className="text-xs text-neutral-500 mb-1">Error details:</p>
                <pre className="text-xs text-red-400 overflow-auto max-h-32">
                  {this.state.error.toString()}
                </pre>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  const [currentPage, setCurrentPage] = useState('landing');

  return (
    <ErrorBoundary>
      <WorkspaceProvider>
        {currentPage === 'landing' ? (
          <LandingPage onNavigate={() => setCurrentPage('dashboard')} />
        ) : (
          <Dashboard />
        )}
      </WorkspaceProvider>
    </ErrorBoundary>
  );
}

export default App;
