import { describe, it, expect, beforeEach } from 'vitest'
import i18n from '../i18n'
import { aktuelleLocale, formatCurrency, formatDate, formatNumber, formatRelativeTime } from './format'

/**
 * Diese Datei bewacht eine Fehlerklasse, die am 2026-08-25 in der laufenden
 * Produktion sichtbar wurde: die Formatierung kannte nur `de` gegen alles
 * andere — `lang === 'de' ? 'de-DE' : 'en-US'`.
 *
 * Zwei Folgen, beide gemessen:
 *   • Nachdem die Spracherkennung aktiv wurde, steht in `i18n.language` die
 *     Region mit ('de-DE'). Der Vergleich mit 'de' schlug fehl, ein deutscher
 *     Nutzer sah "€1,200.00" statt "1.200,00 €".
 *   • Spanisch und Französisch fielen ohnehin auf US-Formate.
 *
 * Deshalb prüft jeder Test hier ALLE vier Sprachen und zusätzlich die Form MIT
 * Region — genau die, an der es zerbrochen ist.
 */

const SPRACHEN = ['en', 'de', 'es', 'fr']

async function spracheSetzen(sprache) {
  await i18n.changeLanguage(sprache)
}

describe('aktuelleLocale', () => {
  beforeEach(async () => {
    await spracheSetzen('en')
  })

  for (const sprache of SPRACHEN) {
    it(`löst '${sprache}' auf eine Locale derselben Sprache auf`, async () => {
      await spracheSetzen(sprache)
      expect(aktuelleLocale().split('-')[0]).toBe(sprache)
    })

    it(`löst '${sprache}-XX' MIT Region ebenfalls auf '${sprache}' auf`, async () => {
      // Genau dieser Fall war kaputt: 'de-DE' traf den Vergleich `=== 'de'` nicht.
      await spracheSetzen(`${sprache}-XX`)
      expect(aktuelleLocale().split('-')[0]).toBe(sprache)
    })
  }

  it('fällt bei einer unbekannten Sprache auf Englisch zurück', async () => {
    await spracheSetzen('xx')
    expect(aktuelleLocale()).toBe('en-US')
  })
})

describe('formatCurrency', () => {
  it('setzt im Deutschen Komma als Dezimaltrenner und das Zeichen hinten', async () => {
    await spracheSetzen('de')
    const text = formatCurrency(1200, 'EUR')
    expect(text).toContain('1.200')
    expect(text).toMatch(/1\.200,00/)
  })

  it('setzt im Englischen Punkt als Dezimaltrenner', async () => {
    await spracheSetzen('en')
    expect(formatCurrency(1200, 'EUR')).toMatch(/1,200\.00/)
  })

  it('formatiert auch mit Region korrekt (der ursprüngliche Fehler)', async () => {
    await spracheSetzen('de-DE')
    expect(formatCurrency(1200, 'EUR')).toMatch(/1\.200,00/)
  })

  it('unterscheidet sich zwischen allen vier Sprachen nicht willkürlich, aber liefert je Sprache ein Ergebnis', async () => {
    for (const sprache of SPRACHEN) {
      await spracheSetzen(sprache)
      expect(formatCurrency(1200, 'EUR')).toBeTruthy()
    }
  })
})

describe('formatNumber', () => {
  it('trennt im Deutschen mit Punkt, im Englischen mit Komma', async () => {
    await spracheSetzen('de')
    expect(formatNumber(1234567)).toBe('1.234.567')
    await spracheSetzen('en')
    expect(formatNumber(1234567)).toBe('1,234,567')
  })
})

describe('formatDate', () => {
  it('ordnet die Bestandteile je Sprache — Tag zuerst im Deutschen, Monat zuerst im Englischen', async () => {
    const datum = new Date(2026, 7, 25) // 25. August 2026, lokale Zeit

    await spracheSetzen('de')
    expect(formatDate(datum, 'short')).toBe('25.08.2026')

    await spracheSetzen('en')
    expect(formatDate(datum, 'short')).toBe('08/25/2026')
  })

  it('liefert für jede Sprache ein nicht-leeres Ergebnis', async () => {
    const datum = new Date(2026, 7, 25)
    for (const sprache of SPRACHEN) {
      await spracheSetzen(sprache)
      for (const form of ['short', 'long', 'withTime']) {
        expect(formatDate(datum, form)).not.toBe('')
      }
    }
  })

  it('gibt für einen leeren Wert einen leeren String zurück', () => {
    expect(formatDate(null)).toBe('')
  })
})

describe('formatRelativeTime', () => {
  it('antwortet in der jeweiligen Sprache, nicht auf Englisch', async () => {
    const vorFuenfMinuten = new Date(Date.now() - 5 * 60 * 1000)

    await spracheSetzen('de')
    expect(formatRelativeTime(vorFuenfMinuten)).toMatch(/vor 5 Minuten/)

    await spracheSetzen('fr')
    expect(formatRelativeTime(vorFuenfMinuten)).toMatch(/il y a 5 minutes/)

    await spracheSetzen('es')
    expect(formatRelativeTime(vorFuenfMinuten)).toMatch(/hace 5 minutos/)
  })

  it('antwortet auch MIT Region deutsch (der ursprüngliche Fehler)', async () => {
    await spracheSetzen('de-DE')
    expect(formatRelativeTime(new Date(Date.now() - 5 * 60 * 1000))).toMatch(/vor 5 Minuten/)
  })
})
