/**
 * Sentry Error Tracking Integration
 *
 * Provides error tracking and performance monitoring for the frontend.
 */

import * as Sentry from '@sentry/react'

/**
 * Initialize Sentry SDK
 *
 * Environment variables (via Vite):
 * - VITE_SENTRY_DSN: Sentry Data Source Name
 * - VITE_SENTRY_ENVIRONMENT: Environment name
 * - VITE_SENTRY_RELEASE: Release version
 */
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN

  if (!dsn) {
    console.log('Sentry: DSN not configured, error tracking disabled')
    return false
  }

  const environment = import.meta.env.VITE_SENTRY_ENVIRONMENT || 'development'
  const release = import.meta.env.VITE_SENTRY_RELEASE || 'travelmind-frontend@1.0.0'

  Sentry.init({
    dsn,
    environment,
    release,

    // Performance Monitoring
    tracesSampleRate: import.meta.env.PROD ? 0.1 : 1.0,

    // Session Replay (optional, captures user sessions)
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,

    // Integrations
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: false,
        blockAllMedia: false,
      }),
    ],

    // Filter out non-critical errors
    beforeSend(event, hint) {
      const error = hint.originalException

      // Ignore network errors (user offline, etc.)
      if (error?.message?.includes('Network Error')) {
        return null
      }

      // Ignore cancelled requests
      if (error?.code === 'ECONNABORTED') {
        return null
      }

      // Ignore 401/403 errors (expected auth errors)
      if (error?.response?.status === 401 || error?.response?.status === 403) {
        return null
      }

      return event
    },

    // Don't send PII by default
    sendDefaultPii: false,
  })

  console.log(`Sentry: Initialized (${environment})`)
  return true
}

/**
 * Set user context for error tracking
 * Call after successful login
 */
export function setUserContext(user) {
  if (!user) return

  Sentry.setUser({
    id: String(user.id),
    username: user.username,
    email: user.email,
  })
}

/**
 * Clear user context
 * Call on logout
 */
export function clearUserContext() {
  Sentry.setUser(null)
}

/**
 * Capture an exception manually
 */
export function captureException(error, context = {}) {
  Sentry.withScope((scope) => {
    Object.entries(context).forEach(([key, value]) => {
      scope.setExtra(key, value)
    })
    Sentry.captureException(error)
  })
}

/**
 * Capture a message
 */
export function captureMessage(message, level = 'info', context = {}) {
  Sentry.withScope((scope) => {
    Object.entries(context).forEach(([key, value]) => {
      scope.setExtra(key, value)
    })
    Sentry.captureMessage(message, level)
  })
}

/**
 * Add a breadcrumb for debugging
 */
export function addBreadcrumb(message, category = 'custom', data = {}) {
  Sentry.addBreadcrumb({
    message,
    category,
    data,
    level: 'info',
  })
}

/**
 * Sentry Error Boundary wrapper component
 */
export const SentryErrorBoundary = Sentry.ErrorBoundary

/**
 * Sentry Profiler for performance monitoring
 */
export const SentryProfiler = Sentry.withProfiler
