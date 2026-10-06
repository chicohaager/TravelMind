/**
 * Wächter für die space-x/y-Kompatibilität (tailwind 4, 2026-10-06).
 *
 * tailwind 4 setzt `space-y-*` als margin-bottom an jedes Kind außer dem
 * letzten, tailwind 3 als margin-top an jedes Kind außer dem ersten — mit
 * höherer Spezifität. Beim Upgrade gemessen: die Tagebuchkarte rutschte auf
 * dem Handy um 12 px, weil `.card { margin-bottom }` aus mobile.css jetzt
 * gegen die Abstandsregel gewann.
 *
 * styles/index.css stellt deshalb für jeden verwendeten Wert die v3-Regel
 * her. Ein neuer Wert im Quelltext ohne Regel dort fiele still auf das
 * v4-Verhalten zurück — dieser Test verlangt die Regel.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const hier = dirname(fileURLToPath(import.meta.url))
const srcVerzeichnis = join(hier, '..')
const css = readFileSync(join(srcVerzeichnis, 'styles', 'index.css'), 'utf8')

function dateien(verzeichnis) {
  const raus = []
  for (const eintrag of readdirSync(verzeichnis)) {
    const pfad = join(verzeichnis, eintrag)
    if (statSync(pfad).isDirectory()) {
      if (eintrag === 'locales' || eintrag === 'node_modules' || eintrag === 'test') continue
      raus.push(...dateien(pfad))
    } else if (/\.(jsx?|tsx?)$/.test(eintrag)) {
      raus.push(pfad)
    }
  }
  return raus
}

const KLASSE = /(?<![\w-])((?:sm|md|lg|xl|2xl):)?space-([xy])-(\d+(?:\.\d+)?|px)(?![\w.-])/g

function verwendeteKlassen(text) {
  return [...text.matchAll(KLASSE)].map((m) => m[0])
}

function hatRegel(klasse) {
  const selektor = '.' + klasse.replace(':', '\\:').replace('.', '\\.')
  return css.includes(`${selektor} > :not([hidden]) ~ :not([hidden])`) &&
    css.includes(`:where(${selektor} > :not(:last-child))`)
}

describe('space-x/y verhalten sich wie unter tailwind 3', () => {
  const gefunden = new Set()
  for (const datei of dateien(srcVerzeichnis)) {
    for (const k of verwendeteKlassen(readFileSync(datei, 'utf8'))) gefunden.add(k)
  }

  it('Positivkontrolle: der Scanner findet Klassen im Quelltext', () => {
    expect(gefunden.size).toBeGreaterThan(5)
    expect(gefunden.has('space-y-4')).toBe(true)
  })

  it('Positivkontrolle: der Scanner erkennt Varianten und Bruchwerte', () => {
    expect(verwendeteKlassen('a sm:space-y-6 b space-y-1.5 c')).toEqual(['sm:space-y-6', 'space-y-1.5'])
    // Gegenkontrolle: ähnliche Namen lösen NICHT aus.
    expect(verwendeteKlassen('my-space-y-4 space-y-reverse')).toEqual([])
  })

  it('Gegenkontrolle: ein Wert ohne Regel wird erkannt', () => {
    expect(hatRegel('space-y-7')).toBe(false)
  })

  it('jeder verwendete Wert hat eine v3-Regel in styles/index.css', () => {
    const fehlend = [...gefunden].filter((k) => !hatRegel(k)).sort()
    expect(fehlend).toEqual([])
  })
})
