/**
 * Wächter: in der Oberfläche steht € als Geldsymbol, nicht $.
 *
 * Am 2026-08-26 trug jede Geldstelle der App das lucide-Symbol `DollarSign` —
 * das Budget-Feld einer Reise, die Budget-Seite, die Sidebar, die Kosten an
 * Orten und Empfehlungen: überall ein `$`, obwohl die Anwendung durchgehend
 * in EUR rechnet (`currency = Column(String(3), default="EUR")` in allen drei
 * Backend-Modellen, `formatCurrency(amount, currency = 'EUR')` im Frontend).
 *
 * Der Fehler ist besonders zäh, weil er nirgends „falsch" aussieht: der
 * Import ist gültig, das Symbol existiert, der Build ist grün. Nur der Nutzer
 * sieht die falsche Währung.
 *
 * Geprüft wird der QUELLTEXT, nicht ein gerendertes Bild — ein Icon ist genau
 * das, was ein Snapshot-Test nicht unterscheidet.
 *
 * Nicht geprüft und mit Absicht erlaubt: `USD ($)` als AUSWAHL in den
 * Währungs-Dropdowns (TripModal, ExpenseModal, PlaceModal) und das `$` in
 * `locales/en/format.json`. Wer in Dollar bezahlt, soll das eintragen können.
 */

import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
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

// Genau EINE Ausnahme, auf den Dateinamen begrenzt: diese Datei nennt das
// verbotene Symbol notgedrungen selbst und würde sich sonst dauerhaft selbst
// beanstanden. Beim ersten Lauf ist genau das passiert. Die Ausnahme muss
// enger sein als die Regel — deshalb ein exakter Pfadvergleich und kein
// Muster wie „alles unter test/", das den Wächter für den ganzen Testordner
// blind machen würde.
const EIGENE_DATEI = join('test', 'waehrungssymbol.test.js')

const quellen = dateien(srcVerzeichnis)
  .map((pfad) => ({
    pfad: relative(srcVerzeichnis, pfad),
    inhalt: readFileSync(pfad, 'utf8'),
  }))
  .filter(({ pfad }) => pfad !== EIGENE_DATEI)

describe('Währungssymbol', () => {
  it('findet überhaupt Quelldateien', () => {
    // Positivkontrolle: ohne sie wäre der Test unten auch dann grün, wenn
    // `dateien()` eine leere Liste zurückgäbe.
    expect(quellen.length).toBeGreaterThan(50)
  })

  it('benutzt nirgends das DollarSign-Symbol', () => {
    const treffer = quellen
      .filter(({ inhalt }) => /\bDollarSign\b/.test(inhalt))
      .map(({ pfad }) => pfad)
    expect(treffer).toEqual([])
  })

  it('benutzt das Euro-Symbol an den Geldstellen', () => {
    // Gegenkontrolle zur Zeile darüber: „kein DollarSign" wäre auch erfüllt,
    // wenn jemand das Symbol ersatzlos gelöscht hätte.
    const mitEuro = quellen.filter(({ inhalt }) => /\bEuro\b/.test(inhalt)).map(({ pfad }) => pfad)
    expect(mitEuro).toContain('pages/Budget.jsx')
    expect(mitEuro).toContain('components/BudgetView.jsx')
    expect(mitEuro).toContain('components/layout/Sidebar.jsx')
    expect(mitEuro.length).toBeGreaterThanOrEqual(9)
  })
})
