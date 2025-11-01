/**
 * Format API error for display
 * Handles both string errors and Pydantic validation error arrays
 */
export function formatError(error, defaultMessage = 'Ein Fehler ist aufgetreten') {
  // Check if error has response data
  if (!error.response?.data) {
    return error.message || defaultMessage
  }

  const { detail } = error.response.data

  // If detail is a string, return it directly
  if (typeof detail === 'string') {
    return detail
  }

  // If detail is an array (Pydantic validation errors)
  if (Array.isArray(detail)) {
    // Format validation errors into readable messages
    const messages = detail.map(err => {
      const field = err.loc?.join('.') || 'unknown'
      const message = err.msg || 'Invalid value'
      return `${field}: ${message}`
    })
    return messages.join(', ')
  }

  // If detail is an object, try to stringify it
  if (typeof detail === 'object') {
    return JSON.stringify(detail)
  }

  return defaultMessage
}

/**
 * Show error toast with proper formatting
 */
export function showErrorToast(toast, error, defaultMessage) {
  const message = formatError(error, defaultMessage)
  toast.error(message)
}
