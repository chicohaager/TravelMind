import React from 'react'
import { useTranslation } from 'react-i18next'

class ErrorBoundaryClass extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })
    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error Boundary caught an error:', error, errorInfo)
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ? (
        this.props.fallback(this.state.error, this.handleReset)
      ) : (
        <ErrorFallback
          error={this.state.error}
          onReset={this.handleReset}
        />
      )
    }

    return this.props.children
  }
}

function ErrorFallback({ error, onReset }) {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
          <svg
            className="w-8 h-8 text-red-600 dark:text-red-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          {t('errors:generic', 'Etwas ist schiefgelaufen')}
        </h2>

        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es erneut.
        </p>

        {process.env.NODE_ENV === 'development' && error && (
          <div className="mb-6 p-4 bg-gray-100 dark:bg-gray-700 rounded-lg text-left overflow-auto max-h-40">
            <p className="text-sm font-mono text-red-600 dark:text-red-400">
              {error.toString()}
            </p>
          </div>
        )}

        <div className="flex gap-3 justify-center">
          <button
            onClick={onReset}
            className="btn-outline"
          >
            Erneut versuchen
          </button>
          <button
            onClick={() => window.location.href = '/'}
            className="btn-primary"
          >
            Zur Startseite
          </button>
        </div>
      </div>
    </div>
  )
}

export default ErrorBoundaryClass
