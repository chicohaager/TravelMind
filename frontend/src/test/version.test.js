/**
 * Wächter gegen auseinanderlaufende Versionsangaben.
 *
 * Die Version steht an DREI Stellen: `frontend/package.json`,
 * `backend/main.py` (`version=`) und der Fußzeile der Seitenleiste. Laufen
 * sie auseinander, lässt sich eine Meldung aus dem Betrieb nicht mehr
 * zuordnen — der Nutzer nennt die Zahl aus der Fußzeile, das Protokoll
 * eine andere, und die Suche beginnt an der falschen Stelle.
 *
 * Vor dem 2026-08-25 standen alle drei auf 1.0.0, während die Anwendung
 * längst etwas anderes war. Das fiel nicht auf, weil nichts sie verglich.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const hier = dirname(fileURLToPath(import.meta.url))
const frontend = join(hier, '..', '..')
const wurzel = join(frontend, '..')

const SEMVER = /^\d+\.\d+\.\d+$/

function ausPaket() {
  return JSON.parse(readFileSync(join(frontend, 'package.json'), 'utf8')).version
}

function ausBackend() {
  const s = readFileSync(join(wurzel, 'backend', 'main.py'), 'utf8')
  const m = /^\s*version="(\d+\.\d+\.\d+)",/m.exec(s)
  if (!m) throw new Error('version= in backend/main.py nicht gefunden')
  return m[1]
}

function ausFusszeile() {
  const s = readFileSync(join(frontend, 'src/components/layout/Sidebar.jsx'), 'utf8')
  const m = /TravelMind v(\d+\.\d+\.\d+)/.exec(s)
  if (!m) throw new Error('Versionszeile in der Seitenleiste nicht gefunden')
  return m[1]
}

describe('Version', () => {
  it('alle drei Stellen sind überhaupt lesbar', () => {
    // Positivkontrolle: ohne sie wäre der Vergleich unten auch dann grün,
    // wenn alle drei Leser `undefined` lieferten.
    for (const f of [ausPaket, ausBackend, ausFusszeile]) {
      expect(f()).toMatch(SEMVER)
    }
  })

  it('sie stimmen überein', () => {
    expect({ backend: ausBackend(), fusszeile: ausFusszeile() }).toEqual({
      backend: ausPaket(),
      fusszeile: ausPaket(),
    })
  })

  it('der CHANGELOG kennt die aktuelle Version', () => {
    const changelog = readFileSync(join(wurzel, 'CHANGELOG.md'), 'utf8')
    expect(changelog).toContain(`## [${ausPaket()}]`)
  })

  it('Gegenkontrolle: eine erfundene Version steht NICHT im CHANGELOG', () => {
    const changelog = readFileSync(join(wurzel, 'CHANGELOG.md'), 'utf8')
    expect(changelog).not.toContain('## [99.99.99]')
  })
})
