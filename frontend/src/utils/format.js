import i18n from '../i18n'

/**
 * Format a date according to the current language
 * @param {Date|string} date - The date to format
 * @param {string} format - 'short', 'long', or 'withTime'
 * @returns {string} Formatted date string
 */
export const formatDate = (date, format = 'short') => {
  if (!date) return ''

  const dateObj = typeof date === 'string' ? new Date(date) : date
  const lang = i18n.language || 'en'

  const options = {
    short: {
      en: { month: 'numeric', day: 'numeric', year: 'numeric' },
      de: { day: '2-digit', month: '2-digit', year: 'numeric' }
    },
    long: {
      en: { month: 'long', day: 'numeric', year: 'numeric' },
      de: { day: 'numeric', month: 'long', year: 'numeric' }
    },
    withTime: {
      en: { month: 'numeric', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' },
      de: { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }
    }
  }

  const locale = lang === 'de' ? 'de-DE' : 'en-US'
  const formatOptions = options[format]?.[lang] || options.short.en

  return dateObj.toLocaleDateString(locale, formatOptions)
}

/**
 * Format currency according to the current language
 * @param {number} amount - The amount to format
 * @param {string} currency - Currency code (EUR, USD, etc.)
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount, currency = 'EUR') => {
  if (amount === null || amount === undefined) return ''

  const lang = i18n.language || 'en'
  const locale = lang === 'de' ? 'de-DE' : 'en-US'

  // Map currency to appropriate locale default if not specified
  const currencyMap = {
    de: 'EUR',
    en: 'USD'
  }

  const finalCurrency = currency || currencyMap[lang]

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: finalCurrency
  }).format(amount)
}

/**
 * Format a number according to the current language
 * @param {number} number - The number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number string
 */
export const formatNumber = (number, decimals = 0) => {
  if (number === null || number === undefined) return ''

  const lang = i18n.language || 'en'
  const locale = lang === 'de' ? 'de-DE' : 'en-US'

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(number)
}

/**
 * Format a relative time (e.g., "2 days ago")
 * @param {Date|string} date - The date to format
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (date) => {
  if (!date) return ''

  const dateObj = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diffMs = now - dateObj
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  const lang = i18n.language || 'en'

  const timeStrings = {
    en: {
      justNow: 'just now',
      minutesAgo: (n) => `${n} minute${n > 1 ? 's' : ''} ago`,
      hoursAgo: (n) => `${n} hour${n > 1 ? 's' : ''} ago`,
      daysAgo: (n) => `${n} day${n > 1 ? 's' : ''} ago`,
      weeksAgo: (n) => `${n} week${n > 1 ? 's' : ''} ago`
    },
    de: {
      justNow: 'gerade eben',
      minutesAgo: (n) => `vor ${n} Minute${n > 1 ? 'n' : ''}`,
      hoursAgo: (n) => `vor ${n} Stunde${n > 1 ? 'n' : ''}`,
      daysAgo: (n) => `vor ${n} Tag${n > 1 ? 'en' : ''}`,
      weeksAgo: (n) => `vor ${n} Woche${n > 1 ? 'n' : ''}`
    }
  }

  const strings = timeStrings[lang] || timeStrings.en

  if (diffSecs < 60) return strings.justNow
  if (diffMins < 60) return strings.minutesAgo(diffMins)
  if (diffHours < 24) return strings.hoursAgo(diffHours)
  if (diffDays < 7) return strings.daysAgo(diffDays)

  const diffWeeks = Math.floor(diffDays / 7)
  return strings.weeksAgo(diffWeeks)
}
