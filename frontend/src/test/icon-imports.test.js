/**
 * Wächter gegen eine Absturz-Fehlerklasse, gefunden am 2026-08-25.
 *
 * `IconSelector.jsx` importierte `Museum` aus lucide-react. Das Symbol gibt
 * es in Version 0.309 NICHT — der Import ergibt `undefined`, und React wirft
 * beim Rendern „Element type is invalid". Die Komponente war schlicht nicht
 * darstellbar.
 *
 * Warum das lange unsichtbar blieb: der Import ist syntaktisch gültig, das
 * Bündel baut fehlerfrei, eslint schweigt (es kennt den Paketinhalt nicht),
 * und die Komponente wird derzeit nirgends benutzt. Erst das Mounten in der
 * Barrierefreiheits-Suite hat sie zum Absturz gebracht.
 *
 * Diese Prüfung fragt das INSTALLIERTE Paket, nicht eine Liste im Kopf —
 * beim nächsten Versionssprung von lucide-react kann ein Symbol wieder
 * verschwinden, und dann fällt es hier auf und nicht beim Nutzer.
 */

import { describe, it, expect } from 'vitest'
import * as lucide from 'lucide-react'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const hier = dirname(fileURLToPath(import.meta.url))
const srcVerzeichnis = join(hier, '..')

function dateien(verzeichnis) {
  const raus = []
  for (const eintrag of readdirSync(verzeichnis)) {
    const pfad = join(verzeichnis, eintrag)
    if (statSync(pfad).isDirectory()) {
      if (eintrag === 'locales' || eintrag === 'node_modules') continue
      raus.push(...dateien(pfad))
    } else if (eintrag.endsWith('.jsx') || eintrag.endsWith('.js')) {
      raus.push(pfad)
    }
  }
  return raus
}

function importierteSymbole() {
  const treffer = []
  for (const datei of dateien(srcVerzeichnis)) {
    const inhalt = readFileSync(datei, 'utf8')
    const block = inhalt.match(/import\s*\{([^}]+)\}\s*from\s*'lucide-react'/s)
    if (!block) continue
    // Kommentare ZUERST entfernen, dann trennen. Umgekehrt zerfällt ein
    // Kommentar mit Komma in mehrere Bruchstücke, und die Marker `//` gehen
    // dabei verloren — beim ersten Lauf am 2026-08-25 genau so passiert:
    // zwei Satzfetzen wurden als fehlende Symbole gemeldet.
    const ohneKommentare = block[1].replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '')
    for (const roh of ohneKommentare.split(',')) {
      const name = roh
        .trim()
        .split(/\s+as\s+/)[0]
        .trim()
      // Nur gültige Bezeichner — alles andere ist kein Import.
      if (/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(name)) {
        treffer.push({ name, datei: relative(srcVerzeichnis, datei) })
      }
    }
  }
  return treffer
}

describe('Symbole: jeder Import existiert im installierten Paket', () => {
  const symbole = importierteSymbole()

  it('findet überhaupt Importe', () => {
    // Positivkontrolle: ohne diese Zeile wäre die Prüfung darunter auch dann
    // grün, wenn der Scanner nichts findet.
    expect(symbole.length).toBeGreaterThan(100)
  })

  it('kein Import ergibt undefined', () => {
    const fehlend = symbole
      .filter(({ name }) => typeof lucide[name] === 'undefined')
      .map(({ name, datei }) => `${name} (${datei})`)
    expect(fehlend).toEqual([])
  })

  it('Positivkontrolle: ein erfundener Name würde auffallen', () => {
    expect(typeof lucide.DiesesSymbolGibtEsNicht).toBe('undefined')
  })

  it('Gegenkontrolle: ein echtes Symbol ist eine Komponente', () => {
    expect(typeof lucide.MapPin).not.toBe('undefined')
  })
})
