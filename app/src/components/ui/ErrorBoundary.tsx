import { Component, type ReactNode } from 'react'
import type { ErrorInfo } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary]', error)
    console.error('[ErrorBoundary] errorInfo:', errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }
      return <ErrorFallback error={this.state.error} onReset={() => this.setState({ hasError: false, error: null })} />
    }
    return this.props.children
  }
}

interface ErrorFallbackProps {
  error: Error | null
  onReset: () => void
}

function ErrorFallback({ error, onReset }: ErrorFallbackProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[200px] p-6 text-center">
      <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">Etwas ist schiefgelaufen</h3>
      <p className="text-sm text-white/40 mb-4 max-w-md">
        Ein unerwarteter Fehler ist aufgetreten. Die Anwendung konnte den Zustand nicht wiederherstellen.
      </p>
      {error && (
        <details className="mb-4 w-full max-w-md text-left">
          <summary className="text-xs text-white/20 cursor-pointer hover:text-white/40">Fehlerdetails anzeigen</summary>
          <pre className="text-xs text-red-400/60 mt-2 bg-black/40 rounded-lg p-3 overflow-auto max-h-32">{error.message}</pre>
        </details>
      )}
      <button
        onClick={onReset}
        className="bg-green-500 hover:bg-green-600 text-black font-medium rounded-xl px-6 py-2 text-sm transition-colors"
      >
        Erneut versuchen
      </button>
    </div>
  )
}

// Re-export for convenience
export { ErrorFallback }