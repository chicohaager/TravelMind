import i18n from '../i18n'

/**
 * Locale-Auflösung für ALLE unterstützten Sprachen.
 *
 * Vorher stand in jeder Funktion `lang === 'de' ? 'de-DE' : 'en-US'`. Das war
 * gleich doppelt falsch:
 *
 *   1. `i18n.language` trägt die Region mit — nach der Spracherkennung steht
 *      dort 'de-DE', nicht 'de'. Der Vergleich schlug also fehl und ein
 *      deutscher Nutzer sah am 2026-08-25 in der Produktion "€1,200.00"
 *      statt "1.200,00 €".
 *   2. Spanisch und Französisch fielen auf 'en-US' — Datum als M/D/YYYY,
 *      Zahlen mit Komma als Tausendertrenner.
 *
 * `resolvedLanguage` ist der Wert, auf den i18next tatsächlich aufgelöst hat;
 * der Split auf den Sprachteil macht die Zuordnung unabhängig von der Region.
 */
const LOCALE_JE_SPRACHE = {
  en: 'en-US',
  de: 'de-DE',
  es: 'es-ES',
  fr: 'fr-FR',
}

export const aktuelleLocale = () => {
  const roh = i18n.resolvedLanguage || i18n.language || 'en'
  const sprache = String(roh).split('-')[0].toLowerCase()
  return LOCALE_JE_SPRACHE[sprache] || LOCALE_JE_SPRACHE.en
}

/**
 * Format a date according to the current language
 * @param {Date|string} date - The date to format
 * @param {string} format - 'short', 'long', or 'withTime'
 * @returns {string} Formatted date string
 */
export const formatDate = (date, format = 'short') => {
  if (!date) return ''

  const dateObj = typeof date === 'string' ? new Date(date) : date

  // Eine Optionsmenge fuer alle Sprachen: die Reihenfolge der Bestandteile
  // waehlt Intl anhand der Locale selbst (en-US -> 08/25/2026, de-DE ->
  // 25.08.2026). Eine Tabelle je Sprache waere genau die Stelle, an der die
  // naechste Sprache wieder vergessen wird.
  const optionen = {
    short: { day: '2-digit', month: '2-digit', year: 'numeric' },
    long: { day: 'numeric', month: 'long', year: 'numeric' },
    withTime: {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    },
  }

  return dateObj.toLocaleDateString(aktuelleLocale(), optionen[format] || optionen.short)
}

/**
 * Format currency according to the current language
 * @param {number} amount - The amount to format
 * @param {string} currency - Currency code (EUR, USD, etc.)
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount, currency = 'EUR') => {
  if (amount === null || amount === undefined) return ''

  return new Intl.NumberFormat(aktuelleLocale(), {
    style: 'currency',
    currency: currency || 'EUR',
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

  return new Intl.NumberFormat(aktuelleLocale(), {
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
  const jetzt = new Date()
  const sekunden = Math.floor((jetzt - dateObj) / 1000)

  // Intl.RelativeTimeFormat statt fest verdrahteter Textbausteine.
  //
  // Vorher lag hier eine Tabelle mit englischen und deutschen Strings, ausgewaehlt
  // ueber `i18n.language`. Die traf Spanisch und Franzoesisch gar nicht — und seit
  // die Spracherkennung 'de-DE' liefert, auch Deutsch nicht mehr: `timeStrings['de-DE']`
  // ist undefiniert, also fiel selbst die deutsche Oberflaeche auf Englisch zurueck.
  // Intl kennt die Formen aller vier Sprachen einschliesslich Plural.
  const formatierer = new Intl.RelativeTimeFormat(aktuelleLocale(), { numeric: 'auto' })

  const stufen = [
    ['second', 60],
    ['minute', 60],
    ['hour', 24],
    ['day', 7],
    ['week', 4.34524],
    ['month', 12],
    ['year', Infinity],
  ]

  let wert = sekunden
  for (const [einheit, teiler] of stufen) {
    if (Math.abs(wert) < teiler) {
      return formatierer.format(-Math.round(wert), einheit)
    }
    wert = wert / teiler
  }
  return formatierer.format(-Math.round(wert), 'year')
}
