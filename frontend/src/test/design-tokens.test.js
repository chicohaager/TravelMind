/**
 * Wächter für die Gestaltung „Adria" (2026-08-25).
 *
 * Drei Fehlerklassen, die alle drei schon vorlagen:
 *
 *  1. **Farben, die die Token umgehen.** 38 `indigo-*`-Klassen und 13
 *     hartcodierte `#6366F1` standen im Quelltext. Ein Farbwechsel im
 *     Tailwind-Token hätte sie NICHT erreicht — die halbe Anwendung wäre
 *     indigo geblieben, und niemand hätte es an einer Datei gesehen.
 *
 *  2. **Schriften aus dem Netz.** Inter und Poppins kamen von
 *     fonts.googleapis.com. In einer App, die offline funktionieren soll,
 *     ist das die falsche Abhängigkeit: beim ersten Aufruf ohne Netz gibt es
 *     keine Schrift.
 *
 *  3. **Kontraste, die nur gut aussehen.** Beim Entwurf gemessen: weiße
 *     Schrift auf `secondary-500` ergibt 3,82:1 — zu wenig für Fließtext.
 *     Diese Prüfung rechnet nach, statt es dem Auge zu überlassen.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname, basename } from 'node:path'
import { fileURLToPath } from 'node:url'

const hier = dirname(fileURLToPath(import.meta.url))
const srcVerzeichnis = join(hier, '..')
const wurzel = join(srcVerzeichnis, '..')

function dateien(verzeichnis, endungen) {
  const raus = []
  for (const eintrag of readdirSync(verzeichnis)) {
    const pfad = join(verzeichnis, eintrag)
    if (statSync(pfad).isDirectory()) {
      if (eintrag === 'locales' || eintrag === 'node_modules') continue
      raus.push(...dateien(pfad, endungen))
    } else if (endungen.some((e) => eintrag.endsWith(e))) {
      raus.push(pfad)
    }
  }
  return raus
}

// ── Kontrast nach WCAG 2.1 ──────────────────────────────────────────────────

function leuchtdichte(hex) {
  const teil = (i) => parseInt(hex.slice(i, i + 2), 16) / 255
  const f = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * f(teil(1)) + 0.7152 * f(teil(3)) + 0.0722 * f(teil(5))
}

function kontrast(a, b) {
  const [hell, dunkel] = [leuchtdichte(a), leuchtdichte(b)].sort((x, y) => y - x)
  return (hell + 0.05) / (dunkel + 0.05)
}

const WEISS = '#FFFFFF'

describe('Gestaltung: der Kontrastrechner selbst', () => {
  it('Positivkontrolle: Schwarz auf Weiß ist 21:1', () => {
    expect(kontrast('#000000', WEISS)).toBeCloseTo(21, 1)
  })

  it('Positivkontrolle: Weiß auf Weiß ist 1:1', () => {
    expect(kontrast(WEISS, WEISS)).toBeCloseTo(1, 3)
  })
})

describe('Gestaltung: Farbwerte kommen aus den Token', () => {
  const quellen = dateien(srcVerzeichnis, ['.js', '.jsx', '.css']).filter(
    (d) => !/\.(test|spec)\.jsx?$/.test(basename(d))
  )

  it('findet überhaupt Quelldateien', () => {
    expect(quellen.length).toBeGreaterThan(40)
  })

  it('keine indigo-Klasse umgeht die Palette', () => {
    const treffer = []
    for (const datei of quellen) {
      readFileSync(datei, 'utf8')
        .split('\n')
        .forEach((zeile, i) => {
          if (/\bindigo-\d{2,3}\b/.test(zeile)) treffer.push(`${basename(datei)}:${i + 1}`)
        })
    }
    expect(treffer).toEqual([])
  })

  it('kein hartcodiertes Indigo #6366F1 mehr im Quelltext', () => {
    const treffer = quellen.filter((d) => /#6366f1/i.test(readFileSync(d, 'utf8'))).map(basename)
    expect(treffer).toEqual([])
  })

  it('Positivkontrolle: der Scanner erkennt einen künstlichen Verstoß', () => {
    expect(/\bindigo-\d{2,3}\b/.test('className="bg-indigo-500"')).toBe(true)
    expect(/#6366f1/i.test('color: #6366F1')).toBe(true)
  })

  it('Gegenkontrolle: die Token-Schreibweise löst NICHT aus', () => {
    expect(/\bindigo-\d{2,3}\b/.test('className="bg-primary-500"')).toBe(false)
  })
})

describe('Gestaltung: Schriften werden selbst ausgeliefert', () => {
  it('index.html lädt nichts von Google', () => {
    const html = readFileSync(join(wurzel, 'index.html'), 'utf8')
    expect(html).not.toMatch(/fonts\.(googleapis|gstatic)\.com/)
  })

  // Kommentare werden entfernt, BEVOR gesucht wird. Sonst schlägt die
  // Prüfung an der Begründung an, die genau diese Domain nennt — beim ersten
  // Lauf am 2026-08-25 genau so passiert (2 Fehlalarme, beide meine eigenen
  // Kommentare). Ein Scanner, der Prosa für Code hält, wird weggeklickt.
  const ohneKommentare = (text) =>
    text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')

  it('keine Quelldatei verweist auf Google Fonts', () => {
    // Testdateien ausgenommen — die Positivkontrolle unten enthaelt die
    // Domain als Code, nicht als Kommentar. Die Ausnahme haengt am
    // DATEINAMEN, nicht am Verzeichnis (Komponententests liegen neben ihrer
    // Komponente).
    const quellen = dateien(srcVerzeichnis, ['.css', '.js', '.jsx']).filter(
      (d) => !/\.(test|spec)\.jsx?$/.test(basename(d))
    )
    const treffer = quellen.filter((d) =>
      /fonts\.(googleapis|gstatic)\.com/.test(ohneKommentare(readFileSync(d, 'utf8')))
    )
    expect(treffer.map((d) => basename(d))).toEqual([])
  })

  it('Positivkontrolle: ein echter Verweis wird erkannt, ein Kommentar nicht', () => {
    expect(/fonts\.googleapis\.com/.test(ohneKommentare('@import url("https://fonts.googleapis.com/x");'))).toBe(
      true
    )
    expect(/fonts\.googleapis\.com/.test(ohneKommentare('/* frueher von fonts.googleapis.com */'))).toBe(false)
    expect(/fonts\.googleapis\.com/.test(ohneKommentare('// kam von fonts.googleapis.com'))).toBe(false)
  })

  it('die Schriften kommen als Paket, nicht als Verweis', () => {
    const css = readFileSync(join(srcVerzeichnis, 'styles/index.css'), 'utf8')
    expect(css).toMatch(/@import\s+'@fontsource-variable\/public-sans/)
    expect(css).toMatch(/@import\s+'@fontsource-variable\/newsreader/)
    const paket = JSON.parse(readFileSync(join(wurzel, 'package.json'), 'utf8'))
    expect(paket.dependencies['@fontsource-variable/public-sans']).toBeTruthy()
    expect(paket.dependencies['@fontsource-variable/newsreader']).toBeTruthy()
  })
})

describe('Gestaltung: die Palette hält die Kontrastgrenzen ein', () => {
  const config = readFileSync(join(wurzel, 'tailwind.config.js'), 'utf8')

  function stufe(name, nr) {
    const block = config.split(`${name}: {`)[1]
    const treffer = new RegExp(`\\b${nr}:\\s*'(#[0-9A-Fa-f]{6})'`).exec(block)
    if (!treffer) throw new Error(`${name}-${nr} nicht gefunden`)
    return treffer[1]
  }

  it('die Palette ist überhaupt lesbar', () => {
    expect(stufe('primary', 500)).toMatch(/^#[0-9A-Fa-f]{6}$/)
    expect(stufe('secondary', 500)).toMatch(/^#[0-9A-Fa-f]{6}$/)
  })

  it('weiße Schrift auf primary-500 erfüllt AA (der Standardknopf)', () => {
    // .btn-primary ist `bg-primary-500 text-white` — der meistbenutzte Knopf.
    expect(kontrast(stufe('primary', 500), WEISS)).toBeGreaterThanOrEqual(4.5)
  })

  it('primary-600 als Text auf Weiß erfüllt AA', () => {
    expect(kontrast(stufe('primary', 600), WEISS)).toBeGreaterThanOrEqual(4.5)
  })

  it('weiße Schrift auf secondary-600 erfüllt AA', () => {
    // Festgehalten, WEIL 500 es nicht tut (gemessen 3,82:1). Wer Weiß auf
    // die Signalfarbe setzt, muss 600 nehmen.
    expect(kontrast(stufe('secondary', 600), WEISS)).toBeGreaterThanOrEqual(4.5)
  })

  it('Abzeichen: -800 auf -100 erfüllt AA in beiden Familien', () => {
    // .badge-primary / .badge-secondary in index.css
    expect(kontrast(stufe('primary', 800), stufe('primary', 100))).toBeGreaterThanOrEqual(4.5)
    expect(kontrast(stufe('secondary', 800), stufe('secondary', 100))).toBeGreaterThanOrEqual(4.5)
  })

  it('die beiden Akzente sind klar unterscheidbar', () => {
    // Nicht Kontrast, sondern Farbabstand: zwei Akzente, die sich nur in der
    // Helligkeit unterscheiden, sind für Farbfehlsichtige derselbe Ton.
    const zerlegen = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16))
    const [r1, g1, b1] = zerlegen(stufe('primary', 500))
    const [r2, g2, b2] = zerlegen(stufe('secondary', 500))
    const abstand = Math.hypot(r1 - r2, g1 - g2, b1 - b2)
    expect(abstand).toBeGreaterThan(120)
  })
})
