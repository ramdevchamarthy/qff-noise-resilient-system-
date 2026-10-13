import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Terminal, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Q-ResQ Uncaught Application Error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/';
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#060911] text-slate-100 flex items-center justify-center p-4">
          <div className="max-w-xl w-full bg-[#0b0f19] border border-rose-500/30 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 shrink-0">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-bold text-white tracking-tight">System Interface Error</h1>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800/60 font-semibold">
                    RECOVERY MODE
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  An unexpected client-side error occurred while rendering the Quantum ML interface.
                </p>
              </div>
            </div>

            <div className="bg-[#04060a] border border-slate-800 rounded-xl p-4 font-mono text-xs text-rose-300 overflow-x-auto space-y-2">
              <div className="flex items-center gap-2 text-slate-400 border-b border-slate-800/80 pb-2">
                <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                <span>Exception Details</span>
              </div>
              <div className="text-rose-400 font-semibold break-words">
                {this.state.error?.message || 'Unknown runtime error'}
              </div>
              {this.state.errorInfo?.componentStack && (
                <pre className="text-[10px] text-slate-500 max-h-36 overflow-y-auto whitespace-pre-wrap">
                  {this.state.errorInfo.componentStack}
                </pre>
              )}
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
              <button
                onClick={this.handleReload}
                className="w-full sm:w-auto flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold transition-all shadow-lg shadow-cyan-950"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Reload Application</span>
              </button>
              <button
                onClick={this.handleReset}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-all"
              >
                <Home className="w-3.5 h-3.5" />
                <span>Reset to Dashboard</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
