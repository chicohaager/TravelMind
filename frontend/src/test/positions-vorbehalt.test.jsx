/**
 * Wächter: eine nur ortsgenaue Position darf auf der Karte nicht wie ein
 * exakter Fund aussehen.
 *
 * Am 2026-08-26 an 16 Orten einer echten Reise gemessen: 9 Positionen waren
 * Gemeindemittelpunkte — der Geocoder hatte die Sache nicht gefunden und war
 * auf den blossen Ortsnamen zurückgefallen. Auf der Karte war das nicht zu
 * sehen: „Aussichtspunkt Repušnica" (Dorfmitte) und „Terme Jezerčica" (echter
 * Fund) waren derselbe Punkt ohne Vorbehalt.
 *
 * Geprüft wird die QUELLE der Komponente, nicht ein gerendertes Bild: das
 * Popup steckt in react-leaflet und lässt sich in jsdom nicht ohne Weiteres
 * öffnen. Dafür ist jede Bedingung hier einzeln sabotierbar — und wurde es.
 */

import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const hier = dirname(fileURLToPath(import.meta.url))
/**
 * ALLE Dateien finden, die einen Ort in einem Karten-Popup darstellen —
 * nicht eine Liste im Kopf.
 *
 * Am 2026-08-26 hat genau das gefehlt: der Hinweis stand in
 * `InteractiveMap.jsx`, der Test war grün, und im Browser fehlte er trotzdem.
 * Die Karte auf der Reiseseite ist eine ZWEITE, in `TripDetail.jsx` inline
 * gebaute Komponente — `InteractiveMap` wird lazy als eigener Chunk geladen
 * und war auf dieser Seite nie aktiv (gemessen: `performance.getEntriesByType`
 * kannte kein TripMap-Bündel).
 *
 * Ein Wächter, der nur einen von zwei Orten kennt, ist eine Zusicherung ohne
 * Prüfung. Deshalb sucht dieser hier selbst.
 */
function dateienMitOrtsPopup() {
  const wurzel = join(hier, '..')
  const raus = []
  const gehe = (verzeichnis) => {
    for (const eintrag of readdirSync(verzeichnis)) {
      const pfad = join(verzeichnis, eintrag)
      if (statSync(pfad).isDirectory()) {
        if (eintrag === 'locales' || eintrag === 'node_modules' || eintrag === 'test') continue
        gehe(pfad)
      } else if (eintrag.endsWith('.jsx')) {
        const inhalt = readFileSync(pfad, 'utf8')
        if (inhalt.includes('<Popup>') && inhalt.includes('place.name')) {
          raus.push({ pfad: relative(wurzel, pfad), inhalt })
        }
      }
    }
  }
  gehe(wurzel)
  return raus
}

const kartenDateien = dateienMitOrtsPopup()

const SPRACHEN = ['de', 'en', 'es', 'fr']

describe('Vorbehalt bei unsicheren Positionen', () => {
  it('findet überhaupt Karten mit Orts-Popups', () => {
    // Positivkontrolle: ohne sie wären alle it.each-Blöcke unten auch dann
    // grün, wenn die Suche nichts fände.
    expect(kartenDateien.length).toBeGreaterThanOrEqual(2)
  })

  it.each(kartenDateien.map((d) => d.pfad))('%s wertet position_unsicher aus', (pfad) => {
    const datei = kartenDateien.find((d) => d.pfad === pfad)
    expect(datei.inhalt).toMatch(/place\.position_unsicher === true/)
  })

  it.each(kartenDateien.map((d) => d.pfad))('%s benutzt den übersetzten Text', (pfad) => {
    const datei = kartenDateien.find((d) => d.pfad === pfad)
    expect(datei.inhalt).toMatch(/t\('map:positionUnsicher'\)/)
  })

  it('nur ein ausdrückliches true löst den Hinweis aus', () => {
    // `position_unsicher` ist DREIWERTIG: null heißt „ungeprüft". Ein
    // wahrheitswertiger Test (`place.position_unsicher &&`) wäre für null
    // ebenfalls falsch — richtig, aber aus Versehen. Der strikte Vergleich
    // hält fest, dass die Dreiwertigkeit gemeint ist.
    for (const { pfad, inhalt } of kartenDateien) {
      expect(inhalt, `${pfad} vergleicht nicht strikt`).toMatch(/place\.position_unsicher === true/)
    }
  })

  it.each(SPRACHEN)('%s kennt den Schlüssel positionUnsicher', (sprache) => {
    const datei = join(hier, '..', 'locales', sprache, 'map.json')
    const texte = JSON.parse(readFileSync(datei, 'utf8'))
    expect(texte.positionUnsicher, `map.json fehlt der Schlüssel in ${sprache}`).toBeTruthy()
    // Gegenkontrolle: kein durchgereichter deutscher Text in den anderen drei.
    if (sprache !== 'de') {
      const de = JSON.parse(readFileSync(join(hier, '..', 'locales', 'de', 'map.json'), 'utf8'))
      expect(texte.positionUnsicher).not.toBe(de.positionUnsicher)
    }
  })
})
